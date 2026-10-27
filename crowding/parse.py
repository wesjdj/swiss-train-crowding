"""Parse the SBB occupancy forecast SIRI-ET zip into tables."""

import re
import zipfile
from pathlib import Path

import pandas as pd
from lxml import etree

NS = "{http://www.siri.org.uk/siri}"
LEVELS = {"manySeatsAvailable": 1, "fewSeatsAvailable": 2, "standingRoomOnly": 3}
LEVEL_LABELS = {1: "Many seats", 2: "Few seats", 3: "Standing room only"}
OPERATORS = {11: "SBB", 33: "BLS", 65: "Thurbo", 82: "SOB", 86: "zb"}
MEMBER = re.compile(r"(\d{4}-\d{2}-\d{2})/operator-(\d+)\.xml$")


def list_members(zip_path: Path) -> list[tuple[str, int, str]]:
    """Return (date, operator, member name) for each XML file in the zip."""
    with zipfile.ZipFile(zip_path) as zf:
        found = [(m.group(1), int(m.group(2)), name) for name in zf.namelist() if (m := MEMBER.search(name))]
    return sorted(found)


def parse_member(zf: zipfile.ZipFile, name: str) -> pd.DataFrame:
    """Parse one operator-day XML file into one row per departure."""
    rows = []
    with zf.open(name) as fh:
        for _, journey in etree.iterparse(fh, tag=f"{NS}EstimatedVehicleJourney"):
            date = journey.findtext(f"{NS}FramedVehicleJourneyRef/{NS}DataFrameRef")
            operator = int(journey.findtext(f"{NS}OperatorRef"))
            train = journey.findtext(f"{NS}TrainNumbers/{NS}TrainNumberRef")
            calls = list(journey.iter(f"{NS}EstimatedCall"))
            dest_id = int(calls[-1].findtext(f"{NS}StopPointRef"))
            dest_name = calls[-1].findtext(f"{NS}StopPointName")
            for seq, call in enumerate(calls):
                departure = call.findtext(f"{NS}AimedDepartureTime")
                if departure is None:
                    continue
                occ = {1: None, 2: None}
                for o in call.iter(f"{NS}ExpectedDepartureOccupancy"):
                    fare_class = 1 if o.findtext(f"{NS}FareClass") == "firstClass" else 2
                    occ[fare_class] = LEVELS.get(o.findtext(f"{NS}OccupancyLevel"))
                rows.append((date, operator, train, seq, int(call.findtext(f"{NS}StopPointRef")),
                             call.findtext(f"{NS}StopPointName"), departure, occ[1], occ[2], dest_id, dest_name))
            journey.clear()
            while journey.getprevious() is not None:
                del journey.getparent()[0]
    df = pd.DataFrame(rows, columns=["date", "operator", "train", "seq", "stop_id", "stop_name",
                                     "departure", "occ_1st", "occ_2nd", "dest_id", "dest_name"])
    df["departure"] = pd.to_datetime(df["departure"], utc=True).dt.tz_convert("Europe/Zurich")
    return df


def parse_zip(zip_path: Path, days: int | None = None) -> pd.DataFrame:
    """Parse the first `days` forecast days of the zip into one departures table."""
    members = list_members(zip_path)
    dates = sorted({d for d, _, _ in members})[:days]
    with zipfile.ZipFile(zip_path) as zf:
        frames = [parse_member(zf, name) for d, _, name in members if d in dates]
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df["operator_name"] = df["operator"].map(OPERATORS).fillna(df["operator"].astype(str))
    df["hour"] = df["departure"].dt.hour
    df["trip_len"] = df.groupby(["date", "operator", "train"])["seq"].transform("max") + 1
    for col in ["occ_1st", "occ_2nd"]:
        df[col] = df[col].astype("Int8")
    return df


def count_levels(zip_path: Path) -> pd.DataFrame:
    """Count occupancy levels per day, class and operator over the whole zip, without full parsing."""
    pattern = re.compile(rb"<FareClass>(\w+)</FareClass>\s*<OccupancyLevel>(\w+)</OccupancyLevel>")
    counts = []
    with zipfile.ZipFile(zip_path) as zf:
        for date, operator, name in list_members(zip_path):
            found = pd.Series([f"{c.decode()}|{lvl.decode()}" for c, lvl in pattern.findall(zf.read(name))])
            for key, n in found.value_counts().items():
                fare_class, level = key.split("|")
                counts.append((date, operator, 1 if fare_class == "firstClass" else 2, LEVELS.get(level), n))
    df = pd.DataFrame(counts, columns=["date", "operator", "fare_class", "level", "n"])
    df["date"] = pd.to_datetime(df["date"])
    df["operator_name"] = df["operator"].map(OPERATORS).fillna(df["operator"].astype(str))
    df["level"] = df["level"].astype("Int8")
    return df
