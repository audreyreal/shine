# you should have received a copy of the opinionated queer license v1.0 along with this program.
# if not, see <https://oql.avris.it/license?c=sweeze>

from time import time_ns
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element
from pathlib import Path
from requests_html import HTMLResponse, HTMLSession, _Find as Find
import rtoml as toml
import keyboard
from tendo.singleton import SingleInstance

# handling config file


def create_config(file_name: str) -> None:
    """Creates a template config file for the specified file name

    Args:
        file_name (str): Filename of the config
    """
    template: dict[str, str | dict | list] = {
        "keybind": "enter",
        "main_nation": "Main Nation for the sake of User Agent",
        "jump_point": "Region Name of jump point, e.g. Artificial Solar System",
        # end prepping and general stuff
        "pointing": False,
        "flag": "flag.png",
        "flag_mode": "must be logo or flag",
        "banner": "banner.png",
        "wfe": """WFE here\n""",
        "embassies": ["Plum Island", "The Brotherhood of Malice"],
        "ro_for_jump_point": [
            "RO in region you want to accept embassies from",
            "Password to said RO",
        ],
        # on to the main nationlist
        "nations": {f"Nation {i + 1}": "password" for i in range(5)},
    }

    toml.dump(template, Path(file_name), pretty=True)


# setting globals now

# set version
VERSION: str = "1.0.0"

# load config
try:
    config: dict[str, str | dict | list] = toml.load(Path("config.toml"))
except FileNotFoundError:
    create_config("config.toml")

# set up session
session: HTMLSession = HTMLSession()
ua: str = f"Shine v{VERSION} (puppet managing helper), devved by nation=sweeze in use by nation={config['main_nation']}"
session.headers["User-Agent"] = ua
# altogether think of this like a browser

# onto all of the functions that actually interact with the site


def make_request(
    url: str,
    payload: dict,
    action: str = "Press enter to continue",
    allow_redirects: bool = False,
    files: dict | None = None,
) -> HTMLResponse:
    """Makes a post request to the specified url with the specified payload

    Args:
        url (str): URL to make the request to
        payload (dict): Payload to send with the request
        action (str, optional): Action to display in the human initialization message. Defaults to "Press enter to continue"
        allow_redirects (bool, optional): Whether or not to allow redirects. Defaults to False
        files (dict, optional): Files to send with the request. Defaults to None

    Returns:
        HTMLResponse: HTMLResponse of the request
    """
    if "api.cgi" not in url.lower():  # checks if the url is an api request
        keybind = config["keybind"]
        print(action.replace("enter", keybind))
        # you can tell my original keybind cant ya <_<
        keyboard.wait(keybind)
        # trigger_on_release doesn't work so i need to replicate its behavior myself
        while True:
            if not keyboard.is_pressed(keybind):
                payload["userclick"] = time_ns()
                break

        # waiting for input so it's a human initiated request and can both do
        # restricted actions and not be bound by the html ratelimit
        # waiting for key bind to be released so the user can't hold it down and spam requests
    else:
        payload["v"] = "11"
        # in case the api changes drastically and unexpectedly breaks shit
    return session.post(url, data=payload, allow_redirects=allow_redirects, files=files)


def login(nation: str, password: str) -> tuple[str, str, str]:
    """Logs into and grabs the chk and local ID of your nation for the sake of security checks

    Args:
        nation (str): Nation you're logging into
        password (str): Password to said nation

    Returns:
        tuple[str, str]: CHK, local ID, and current region
    """
    data: dict[str, str] = {
        "logging_in": "1",
        "nation": nation,
        "password": password,
    }

    url: str = "https://dark.nationstates.net/region=rwby"
    # shoutouts to the relendo snippet that gave me the idea of using a region page to get both chk and localid
    response: HTMLResponse = make_request(
        url, data, f"Press enter to login to {nation}"
    )
    # get the two security check values, chk and localid
    chk: str = response.html.find("input[name=chk]")[0].attrs["value"]
    local_id: str = response.html.find("input[name=localid]")[0].attrs["value"]

    # get current region for sake of deciding whether to move to JP or not
    panel_region_bar: Find = response.html.find("#panelregionbar")[0]
    current_region: str = (
        panel_region_bar.find(".paneltext")[0].text.lower().split("\n")[0]
    )
    # not super proud of that line but it works

    return chk, local_id, current_region


def prep(nation: str, password: str) -> None:
    """Given a nation and it's password, preps the nation to join the WA and move to a specified region

    Args:
        nation (str): Nation to prep
        password (str): Password to said nation
    """
    try:
        chk, local_id, current_region = login(nation, password)
    except Exception:
        print(f"Failed to login to {nation}. Are you sure you have the right password?")
        return
    apply_to_wa(chk)
    if current_region != config["jump_point"].lower():
        move_to_region(config["jump_point"], local_id)


def apply_to_wa(chk: str) -> None:
    """Given a CHK to a nation, applies that nation to the WA

    Args:
        chk (str): CHK to your nation
    """
    data: dict[str, str] = {
        "action": "join_UN",
        "chk": chk,
        "resend": "1",
    }
    url: str = "https://www.nationstates.net/template-overall=none/page=UN_status/"

    response: HTMLResponse = make_request(url, data, "Press enter to apply to the WA")

    if "has been received!" in response.text:
        print("Successfully applied to WA")
    else:
        print("Failed to apply to WA")


def move_to_region(region: str, local_id: str) -> None:
    """Moves your nation to the specified region

    Args:
        region (str): Region to move your nation to
        local_id (str): Local ID of your nation
    """
    # collecting local id
    data: dict[str, str] = {
        "localid": local_id,
        "region_name": region,
        "move_region": "1",
    }
    url: str = "https://www.nationstates.net/template-overall=none/page=change_region"

    response: HTMLResponse = make_request(url, data, f"Press enter to move to {region}")

    if "Success!" in response.text:
        print(f"Successfully moved to {region}")
    else:
        print(f"Failed to move to {region}")


def tag(nation: str, password: str) -> None:
    try:
        chk, region, permissions, embassies = get_perms(nation, password)
    except Exception:
        print(
            f"{nation} is not an RO, does not exist, or has an incorrect password. Skipping..."
        )
        return
    tag_region(chk, region, permissions, embassies)


def tag_region(chk: str, region: str, permissions: list, embassies: list) -> None:
    """Tags a region with the specified permissions and embassies

    Args:
        chk (str): CHK of your RO in the region
        region (str): Region to tag
        permissions (list): List of permissions said RO has
        embassies (list): List of embassies the region has
    """

    if "Appearance" in permissions:
        change_wfe(chk, region, config["wfe"])
        change_flag_and_banner(chk, region, config["flag"], config["banner"])
    if "Embassies" in permissions:
        print(f"{len(embassies)} embassies to close...")
        for embassy in embassies:
            close_embassy(chk, region, embassy)
        for embassy in config["embassies"]:
            open_embassy(chk, region, embassy)


def open_embassy(chk: str, region: str, embassy: str) -> None:
    """Sends an embassy from the specified region to another specified region

    Args:
        chk (str): CHK of your RO in the region
        region (str): Region to send the embassy from
        embassy (str): Region to send the embassy to
    """
    data: dict[str, str] = {
        "embassyregion": embassy,
        "chk": chk,
        "embassyrequest": "1",
    }
    url: str = f"https://www.nationstates.net/template-overall=none/page=region_control/region={region}"

    response: HTMLResponse = make_request(
        url, data, f"Press enter to send embassy to {embassy}"
    )

    if "Your proposal for the construction of embassies with " in response.text:
        print(f"Successfully sent embassy to {embassy}")
    else:
        print(f"Failed to send embassy to {embassy}")


def close_embassy(chk: str, region: str, embassy: str) -> None:
    """Closes an embassy in the specified region

    Args:
        chk (str): CHK of your RO in the region
        region (str): Region you are tagging
        embassy (str): Embassy to close
    """
    if embassy in config["embassies"]:
        cancel_embassy_closure(chk, region, embassy)
        return

    data: dict[str, str] = {
        "chk": chk,
        "page": "region_control",
        "region": region,
        "embassyregion": embassy,
        "cancelembassy": " Withdraw Embassy ",
    }
    url: str = "https://www.nationstates.net/template-overall=none/page=region_control"

    response: HTMLResponse = make_request(url, data, f"Press enter to close {embassy}")

    if "has been scheduled for demolition." in response.text:
        print(f"Successfully closed {embassy}")
    else:
        print(f"Failed to close {embassy}")


def cancel_embassy_closure(chk: str, region: str, embassy: str) -> None:
    """Given a region and embassy, cancel the closure of the embassy

    Args:
        chk (str): _description_
        region (str): _description_
        embassy (str): _description_
    """
    data: dict[str, str] = {
        "chk": chk,
        "page": "region_control",
        "region": region,
        "embassyregion": embassy,
        "cancelembassy": " Cancel Closure ",
    }
    url: str = "https://www.nationstates.net/template-overall=none/page=region_control"

    response: HTMLResponse = make_request(
        url, data, f"Press enter to cancel demolition of {embassy}"
    )

    if "Embassy closure order cancelled." in response.text:
        print(f"Successfully cancelled embassy demolition for {embassy}")
    else:
        print("Embassy was not closing!")


def get_embassy_requests(region: str) -> list:
    """Given a region, gets all of the unopened embassy requests from the Nationstates API

    Args:
        region (str): region you want the embassies of

    Returns:
        list: List of all the embassies
    """
    data: dict[str, str] = {
        "q": "embassies",
        "region": region,
    }
    url: str = "https://www.nationstates.net/cgi-bin/api.cgi"

    response: HTMLResponse = make_request(url, data, f"Getting embassies from {region}")

    root: Element = ET.fromstring(response.text)
    embassies_element: list[Element] = root.findall(".//EMBASSY[@type='invited']")
    embassies: list = [embassy.text for embassy in embassies_element]
    return embassies


def change_wfe(chk: str, region: str, wfe: str) -> None:
    """Changes the WFE of a specified region to the specified WFE

    Args:
        chk (str): CHK of your RO in the region
        region (str): Region to change the WFE of
        wfe (str): WFE to change to
    """
    data: dict[str, str] = {
        "page": "region_control",
        "chk": chk,
        "region": region,
        "message": wfe,
        "setwfebutton": "1",
    }
    url: str = "https://www.nationstates.net/template-overall=none/page=region_control"

    response: HTMLResponse = make_request(
        url, data, f"Press enter to change {region}'s WFE"
    )

    if "World Factbook Entry updated!" in response.text:
        print("Successfully changed WFE")
    else:
        print("Failed to change WFE")


def change_flag_and_banner(chk: str, region: str, flag: str, banner: str) -> None:
    """Changes a specified region's flag and banner to that of user specified ones

    Args:
        chk (str): CHK of your RO in the region
        region (str): Region to change the flag and banner of
        flag (str): Path to flag to change to
        banner (str): Path to banner to change to
    """
    banner_id = upload(chk, region, "banner", banner)
    flag_file = upload(chk, region, "flag", flag)

    data: dict[str, str] = {
        "page": "region_control",
        "chk": chk,
        "region": region,
        "newbanner": banner_id,
        "newflag": flag_file,
        "saveflagandbannerchanges": "1",
        "flagmode": config["flag_mode"],
        "newflagmode": config["flag_mode"],
    }
    url: str = "https://www.nationstates.net/template-overall=none/page=region_control"

    response: HTMLResponse = make_request(
        url, data, f"Press enter to change {region}'s flag and banner"
    )

    if "banner/flag updated!" in response.text:
        print("Successfully changed flag and banner")
    else:
        print("Failed to change flag and banner")


def upload(chk: str, region: str, file_type: str, file: str, _depth=0) -> str:
    """Uploads a specified file to the specified region

    Args:
        chk (str): CHK to your RO in the region
        region (str): Region you are uploading to
        file_type (str): Type of file you are uploading. Will raise ValueError if not "flag" or "banner"
        file (str): Path to the file you are uploading
        _depth (int, not for end user use): Internal use only. Depth of the recursion. Defaults to 0.

    Returns:
        str: ID number of the banner or filename of the flag
    """
    if file_type not in ["flag", "banner"]:
        raise ValueError("file_type must be either 'flag' or 'banner'")

    if _depth > 1:
        return "0"

    files: dict[str, bytes] = {f"file_upload_r{file_type}": open(file, "rb")}
    data: dict[str, str] = {
        "uploadtype": f"r{file_type}",
        "page": "region_control",
        "expect": "json",
        "chk": chk,
        "region": region,
    }
    url: str = "https://www.nationstates.net/cgi-bin/upload.cgi"

    response: HTMLResponse = make_request(
        url, data, f"Press enter to upload {file_type} to {region}", files=files
    )

    if response.status_code == 200:
        print(f"Successfully uploaded {file_type}")
        return str(response.json()["id"])
    else:
        print(
            f"Failed to upload {file_type} with status code {response.status_code}. Retrying..."
        )
        upload(chk, region, file_type, file, _depth=_depth + 1)


def get_perms(nation: str, password: str) -> tuple[str, str, list, list]:
    """Checks whether a specified nation is an RO, and if it is, returns the CHK, the region the nation is RO in, and permissions the nation has

    Args:
        nation (str): Nation to check
        password (str): Password to said nation
    """
    data: dict[str, str] = {
        "nation": nation,
        "password": password,
        "logging_in": "1",
    }
    url: str = "https://www.nationstates.net/template-overall=none/page=region_control"

    response: HTMLResponse = make_request(
        url, data, f"Press enter to check if {nation} is an RO"
    )

    try:
        chk: str = response.html.find("input[name=chk]")[0].attrs["value"]
        region: str = response.html.find(".dull")[0].text
        ro_block: Find = response.html.find(".minorinfo")[0]
        permissions: list = [perm.text for perm in ro_block.find(".operm")]
        embassies: list = [emb.text for emb in response.html.find(".rlink")]
        return chk, region, permissions, embassies
    except Exception:
        return


def tag_and_prep(nations: dict) -> None:
    for nation, password in nations.items():
        tag(nation, password)
        prep(nation, password)


def accept_embassy(chk: str, embassy: str, embassy_hub: str) -> None:
    data: dict[str, str] = {
        "page": "region_control",
        "region": embassy_hub,
        "chk": chk,
        "embassyregion": embassy,
        "acceptembassyrequest": " Accept ",
    }
    url: str = f"https://www.nationstates.net/template-overall=none/page=region_control/region={embassy_hub}"

    response: HTMLResponse = make_request(
        url, data, f"Press enter to accept {embassy}'s request"
    )

    if "has begun!" in response.text:
        print(f"Successfully accepted {embassy}'s request")
    else:
        print(f"Failed to accept {embassy}'s request")


def accept_embassies():
    embassy_hub: str = input("Enter embassy hub: ")
    embassies: list = get_embassy_requests(embassy_hub)
    chk: str = login(*config["ro_for_jump_point"])[0]
    for embassy in embassies:
        accept_embassy(chk, embassy, embassy_hub)


def check_if_nation_exists(nation: str) -> bool:
    data: dict[str, str] = {"nation": nation, "q": "lastlogin"}
    url: str = "https://www.nationstates.net/cgi-bin/api.cgi"

    response: HTMLResponse = make_request(url, data, f"Checking if {nation} exists...")

    try:
        response.raise_for_status()
        return True
    except Exception:
        return False


def main() -> None:
    license_notice: str = "You should have received a copy of the Opinionated Queer License v1.0 with this program.\nIf not, you may view it at https://oql.avris.it/license?c=sweeze\n"
    print(license_notice)
    print(
        "Note that Shine uses the NationStates API. Avoid running any other program that uses the API while this is running, otherwise both will most likely break."
    )

    if not check_if_nation_exists(config["main_nation"]):
        print(
            f"Specified main nation, {config['main_nation']} does not exist. Exiting..."
        )
        return

    nations: dict = config["nations"]

    option_selection: str = (
        "Type 1 to tag and/or prep or 2 to accept embassies on an embassy hub: "
    )

    action: str = input(option_selection)

    match action:
        case "1":
            tag_and_prep(nations)
        case "2":
            accept_embassies()


if __name__ == "__main__":
    me = SingleInstance()
    # to ensure simultaneity cannot be broken, singleinstance closes the program if another instance is already running
    main()
