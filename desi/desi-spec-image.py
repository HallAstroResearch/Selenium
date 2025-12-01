# Copyright (C) 2025 Heptazhou <zhou@0h7z.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#
# Program to download and optionally rename DESI spectrum images
# 
# DONE:
# * Accept SDSS_NAME and use as beginning of output filenema
# * list each image to terminal as it's created
# 
# TO DO:
# * Answer "PBH ? for ZZZ" question below: had to changet netmonitor keys, but what does it do?
# * Rework to accept input list including SDSS_NAME,targetid
# * Output list of DESI spectrum images ( list to screen each one as it's created)
# * Add option to not display in firefox, or only display two DESI spectrum images at a time in firefox (currently loading one & previous one)
# * Goal is to create DESi spectrum images for all objects in AWTQ_DESI_20250703.xlsx on SharePoint

from base64 import b64decode as base64decode
from builtins import isinstance as isa
from pathlib import Path
from re import sub as replace
from sys import platform as PLATFORM
from time import sleep
from typing import Literal, cast

from selenium.common import TimeoutException
from selenium.webdriver import Firefox, FirefoxOptions, Keys
from selenium.webdriver import Remote as Browser

# Misc. functions
def isapple() -> bool:
	return PLATFORM == "darwin"

def filesize(f: Path | str) -> int:
	if not isfile(f): return 0
	if isa(f, Path):
		return (f).stat().st_size
	return Path(f).stat().st_size

def isfile(f: Path | str) -> bool:
	if isa(f, Path):
		return (f).is_file()
	return Path(f).is_file()

def write(f: Path | str, x: bytes | str) -> int:
	if isa(x, bytes):
		with open(f, "wb") as io:
			return io.write(x)
	else:
		with open(f, "wt", newline="") as io:
			return io.write(x)

# mypy: disable-error-code="func-returns-value"

# Set up key combination to bring up the Dock in Firefox
if isapple():
	netmonitor = Keys.COMMAND + Keys.LEFT_ALT + "E"
else:
	netmonitor = Keys.CONTROL + Keys.SHIFT + "E"

# Set up Firefox browser
def init(headless: bool = False) -> Browser:
	# https://wiki.mozilla.org/Firefox/CommandLineOptions
	opt = FirefoxOptions()
	opt.add_argument("-headless") if headless else None
	opt.set_preference("browser.aboutConfig.showWarning", False)
	opt.set_preference("browser.ctrlTab.sortByRecentlyUsed", True)
	opt.set_preference("browser.link.open_newwindow", 3)
	opt.set_preference("browser.menu.showViewImageInfo", True)
	opt.set_preference("browser.ml.enable", False)
	opt.set_preference("datareporting.usage.uploadEnabled", False)
	opt.set_preference("devtools.netmonitor.persistlog", True)
	opt.set_preference("devtools.selfxss.count", 5)
	opt.set_preference("devtools.webconsole.persistlog", True)
	opt.set_preference("devtools.webconsole.timestampMessages", True)
	opt.set_preference("identity.fxaccounts.enabled", False)
	opt.set_preference("pdfjs.externalLinkTarget", 2)
	opt.set_preference("privacy.fingerprintingProtection.overrides", "+AllTargets,-CanvasRandomization,-CanvasImageExtractionPrompt,-CanvasExtractionBeforeUserInputIsBlocked")
	opt.set_preference("privacy.fingerprintingProtection", True)
	opt.set_preference("privacy.spoof_english", 2)
	opt.set_preference("privacy.window.maxInnerHeight", 900)
	opt.set_preference("privacy.window.maxInnerWidth", 1600)
	opt.set_preference("security.OCSP.enabled", 0)
	opt.set_preference("security.pki.crlite_mode", 2)
	opt.set_preference("sidebar.main.tools", "history")
	ret = Firefox(opt)
	ret.set_page_load_timeout(5)
	ret.set_script_timeout(3)
	ret.set_window_size(1600, 900) if headless else None
	return ret

# Load spectrum image from a given data release (dr) of a given DESI targetid (id) 
def load(br: Browser, dr: Literal["edr", "dr1"], id: int | str) -> bytes:
	# https://data.desi.lbl.gov/doc/access/
	br.get(f"https://www.legacysurvey.org/viewer/desi-spectrum/{dr}/targetid{id}")
	js = """return document.querySelector("canvas").toDataURL("image/png")"""
	rv = cast(str, br.execute_script(js))
	br.get(rv)
	rv = replace(r"^data:[^,]*,", "", rv)
	return base64decode(rv)

# Save spectrum image to disk
def save(br: Browser, sdss_name: str, dr: Literal["edr", "dr1"], id: int | str, path: str | None = None) -> None:
#def save(br: Browser, dr: Literal["edr", "dr1"], id: int | str, path: str | None = None) -> None:
	#if path is None: path = f"desi-{dr}-{id}.png"
	if path is None: path = f"{sdss_name}-desi-{dr}-{id}.png"
	br.switch_to.new_window() # new tab
	if filesize(path) > 0: return br.get(Path(path).absolute().as_uri()) # already exists
	br.get("about:logo"), br.switch_to.active_element.send_keys(netmonitor), sleep(1)
	while True:
		try:
			data = load(br, dr, id)
			break
		except TimeoutException: sleep(2)
	write(path, data)
	print(f"{path} created")

# Main program loop
if __name__ == "__main__":
	ff = init()
	save(ff, "081148.27+083240.1", "dr1", 39627991554195594) # https://www.legacysurvey.org/viewer/desi-spectrum/dr1/targetid39627848784286649
	#save(ff, "152348.99-004701.8", "dr1", 39627770480824813) # https://www.legacysurvey.org/viewer/desi-spectrum/dr1/targetid39627848784286649
	#save(ff, "124652.81-081312.9", "dr1", 39627589169449230) # https://www.legacysurvey.org/viewer/desi-spectrum/dr1/targetid39627848784286649
	##save(ff, "dr1", 39627848784286649) # https://www.legacysurvey.org/viewer/desi-spectrum/dr1/targetid39627848784286649
	##save(ff, "dr1", 39627848784285507) # https://www.legacysurvey.org/viewer/desi-spectrum/dr1/targetid39627848784285507
	# ff.quit() # close the browser

