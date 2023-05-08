# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation either version
# 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with NSDotPy. If not, see <https://www.gnu.org/licenses/>.
import logging
import os
import rtoml
from nsdotpy.session import NSSession, canonicalize


def handle_config() -> dict:
    if os.path.exists("config.toml"):
        # load config file
        with open("config.toml", "r") as f:
            config = rtoml.load(f)
        if config["main_nation"] == "Your Main Nation Here":
            print("Please actually fill in config file and run the script again.")
            exit()
    else:
        # no config file, create one
        template = {
            "keybind": "space",  # keybind to use
            "main_nation": "Your Main Nation Here",  # for user agent
            "jump_point": "The Allied Nations of Egalaria",  # for moving to
            "applying": True,
            "pointing": False,
            # if you're not pointing none of these matter until you're at nations
            "detagging": False,
            # if you're detagging none of these matter until you're at nations
            "flag": "flag.gif",
            "flag_mode": "logo",
            "banner": "banner.png",
            "wfe": "wfe\n",
            "ro_for_jump_point": ("Nation", "Password"),
            # doubles as embassies to close when detagging
            "embassies": (
                "Plum Island",
            ),
            "nations": {f"nation {i}": "password" for i in range(1, 6)},
        }
        with open("config.toml", "w") as f:
            rtoml.dump(template, f)
        print(
            "No config file found, created one. Please edit it and run the script again."
        )
        exit()
    return config


def detag(session: NSSession, embassies: set):
    for embassy in embassies:
        if not session.close_embassy(embassy):
            session.abort_embasy(embassy)
        session.change_wfe()
        session.set_flag_and_banner("none", "r1")


def main():
    # load config
    config = handle_config()
    # unpack config into variables
    jp: str = config["jump_point"]
    applying: bool = config["applying"]
    pointing: bool = config["pointing"]
    detagging: bool = config["detagging"]
    flag: str = config["flag"]
    flag_mode: str = config["flag_mode"]
    banner: str = config["banner"]
    wfe: str = config["wfe"]
    ro_for_jump_point: tuple = tuple(config["ro_for_jump_point"])
    embassies: set = set(config["embassies"])
    nations: dict[str, str] = config["nations"]

    session = NSSession(
        "Shine",
        "3.0.1",
        "Sweeze",
        config["main_nation"],
        config["keybind"],
        "github.com/sw33ze/shine"
    )

    nations = order_nations(nations)

    for nation, password in nations.items():
        if session.login(nation, password):
            if pointing:
                if detagging:
                    detag(session, embassies)
                else:
                    tag(flag, flag_mode, banner, wfe, session, embassies)
                # end pointing
            if applying:
                session.apply_wa()
            if session.region != canonicalize(jp):
                session.move_to_region(jp)

def order_nations(nations: dict[str, str]) -> dict[str, str]:
    if start_of_nations := input(
        "If you don't want to start at the start of nations, type the new nation you want to start with. Otherwise, press enter."
    ):
        if canonicalize(start_of_nations) not in canonicalize(nations):
            print("That nation is not in the list of nations. Using default order.")
            return nations
        before_new_start = {}
        for nation, password in list(nations.items()):
            if canonicalize(nation) != canonicalize(start_of_nations):
                before_new_start |= {nation: password}
                nations.pop(nation)
            else:
                nations |= before_new_start
                break
    return nations


def tag(flag, flag_mode, banner, wfe, session: NSSession, embassies):
    session.change_wfe(wfe)
    flag_id = session.upload_to_region("flag", flag)
    banner_id = session.upload_to_region("banner", banner)
    session.set_flag_and_banner(flag_id, banner_id, flag_mode)
    for embassy in embassies:
        if not session.open_embassy(embassy):
            session.cancel_embassy(embassy)



if __name__ == "__main__":
    main()
