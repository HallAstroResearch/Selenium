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


# Program to download and optionally rename DESI spectrum images
#
# DONE:
# * Accept SDSS_NAME and use as beginning of output filenema
# * list each image to terminal as it's created
# * Rework to accept input list including SDSS_NAME,targetid
# * Output list of DESI spectrum images (list to screen each one as it's created)
# * option to not display firefox at all i.e. headless mode (not recommended though)
# * only display two DESI spectrum images at a time in firefox (currently loading one & previous one)
#
# TO DO:
# * Goal is to create DESi spectrum images for all objects in AWTQ_DESI_20250703.xlsx on SharePoint

from base64 import b64decode as base64decode
from builtins import isinstance as isa
from pathlib import Path
from re import sub as replace
from sys import platform as PLATFORM
from time import sleep
from typing import Final, Literal
from urllib.parse import unquote as uri_decode

from pandas import DataFrame, read_csv
from selenium.common import JavascriptException, TimeoutException  # type: ignore[import-not-found]
from selenium.webdriver import Firefox, FirefoxOptions, Keys  # type: ignore[import-not-found]
from selenium.webdriver import Remote as Browser


# Misc. functions
def isapple() -> bool:
	return PLATFORM == "darwin"

def eachrow(df: DataFrame):
	return (df).itertuples(name="DataFrameRow")

def exec_js(br: Browser, js: str):
	return (br).execute_script(js)

def url2bytes(url: str) -> bytes:
	data = replace(r"^data:[^,]*,", "", url)
	return base64decode(data)

def file2url(f: Path | str) -> str:
	if not isa(f, Path): f = Path(f)
	return uri_decode(f.absolute().as_uri())

def filesize(f: Path | str) -> int:
	if not isa(f, Path): f = Path(f)
	return f.stat().st_size if isfile(f) else 0

def isfile(f: Path | str) -> bool:
	if not isa(f, Path): f = Path(f)
	return f.is_file()

def write(f: Path | str, x: bytes | str) -> int:
	if isa(x, bytes):
		with open(f, "wb") as io:
			return io.write(x)
	else:
		with open(f, "wt", newline="") as io:
			return io.write(x)

# mypy: disable-error-code="func-returns-value"

__dir__: Final = Path(__file__).parent

# Set up key combination to bring up the DevTools in Firefox
if isapple():
	netmonitor = Keys.COMMAND + Keys.ALT + "E"
else:
	netmonitor = Keys.CONTROL + Keys.SHIFT + "E"
# https://github.com/SeleniumHQ/selenium/pull/15948 # selenium v4.34.0

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
	opt.set_preference("browser.newtabpage.activity-stream.asrouter.providers.onboarding", "{}") # TAB_GROUP_ONBOARDING_CALLOUT
	opt.set_preference("browser.urlbar.trimURLs", False)
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
	ret.set_page_load_timeout(6)
	ret.set_script_timeout(3)
	ret.set_window_size(1600, 900) if headless else None
	return ret

# Load spectrum image from a given data release (dr) of a given DESI targetid (id)
def load(br: Browser, dr: Literal["edr", "dr1"], id: int | str) -> bytes:
	# https://data.desi.lbl.gov/doc/access/
	br.get(f"https://www.legacysurvey.org/viewer/desi-spectrum/{dr}/targetid{id}")
	v3 = """document.querySelector(`.bk-Column`).shadowRoot.querySelector(`.bk-Row`)
		 .shadowRoot.querySelector(`.bk-Figure`).shadowRoot.querySelector(`.bk-Canvas`)
		 .shadowRoot.querySelector(`canvas`).toDataURL(`image/png`)""" # lines label missing
	v3 = """var _bk_col_row_fig = Object.values(Bokeh.index)[0].child_views[0].child_views[0]
			return _bk_col_row_fig.export()._canvas.toDataURL(`image/png`)"""
	v2 = """return document.querySelector(`canvas`).toDataURL(`image/png`)"""
	try:
		rv = str(exec_js(br, v2))
	except JavascriptException:
		js = "return performance.getEntriesByType(`navigation`)[0].responseStatus"
		if (code := int(exec_js(br, js))) >= 400: raise Exception(code) # Client/Server error
		f, g, h = __dir__ / f"html/desi-{dr}-{id}.html", "</html>", br.current_url
		br.get(f"view-source:{h}")
		rv = str(exec_js(br, f"return document.body.textContent"))
		write(f"{f}.orig", rv + "\n"), write(f, rv[:rv.find(g) + len(g)] + "\n")
		br.get(file2url(f))
		rv = str(exec_js(br, v3))
	br.get(rv)
	return url2bytes(rv)

# Save spectrum image to disk
def save(br: Browser, dr: Literal["edr", "dr1"], id: int | str, dst: Path | str = "", log_prefix: str = "") -> bool:
	dst = Path(dst or f"desi-{dr}-{id}.png")
	br.switch_to.new_window() # new tab
	if filesize(dst) > 0: return br.get(file2url(dst)) or True # already exists
	br.get("about:logo"), br.switch_to.active_element.send_keys(netmonitor), sleep(1)
	while True:
		try:
			data = load(br, dr, id)
			break
		except TimeoutException: sleep(3)
		except JavascriptException as e: # unlikely
			print(log_prefix + "ignored", dr, id, f"\n{e}")
			return False
	write(dst, data)
	print(log_prefix + "created", dr, id, "@", dst.as_posix())
	return True

def close_oldest(br: Browser, keep_ntab: int) -> None:
	while len(br.window_handles) > max(keep_ntab, +1):
		br.switch_to.window(br.window_handles[+0]) # oldest tab
		br.close()
	else: # finally
		br.switch_to.window(br.window_handles[-1]) # newest tab

# Main program
if __name__ == "__main__":
	ff = init()
	df = read_csv(__dir__ / "AWTQ_DESI_20250703DR1.tsv", sep="\t")
	df = df[:20]
	dr: Final = "dr1"
	path = __dir__ / "spec"
	imgs, i = list[str](), 0
	nrow_ndigit = len(str(nrow := len(df)))
	for row in eachrow(df):
		img_name = f"{row.SDSS_NAME}-desi-{dr}-{row.targetid}.png"
		progress = f"[%{nrow_ndigit}d/{nrow}] " % (i := i + 1)
		save(ff, dr, row.targetid, path / img_name, progress) and imgs.append(img_name)
		close_oldest(ff, 2) # keep at most 2 tabs
	else: print("finished"), print(f"\n{len(imgs)} image(s) ready")
	for x in imgs: print(x)
	# save(ff, "dr1", 39627802856653317) # https://www.legacysurvey.org/viewer/desi-spectrum/dr1/targetid39627802856653317 # v3.8.0 #!broken
	# save(ff, "dr1", 39627848784285507) # https://www.legacysurvey.org/viewer/desi-spectrum/dr1/targetid39627848784285507 # v2.4.3
	# save(ff, "dr1", 39627848784286649) # https://www.legacysurvey.org/viewer/desi-spectrum/dr1/targetid39627848784286649 # v2.4.3
	ff.quit() # close the browser

