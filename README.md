# Swiss train crowding forecast

When and where are Swiss trains crowded? This project uses the SBB
[Occupancy Forecast SIRI Dataset](https://opendata.swiss/en/dataset/occupancy-forecast-siri-dataset)
from opendata.swiss. The dataset gives the expected occupancy of SBB, BLS, Thurbo, SOB and
Zentralbahn trains for the next three months, for each stop and each class.

- **App:** https://renkulab.io/p/wes/swiss-train-crowding/apps/01M5YDX563ZYWVE7AZR7X0E7V5
- **Renku project:** https://renkulab.io/p/wes/swiss-train-crowding

## Findings

- The evening rush (16:00–18:00) is a bit stronger and longer than the morning rush.
- Christmas Day and New Year's Day are the quietest days in the forecast.
- Geneva's Léman Express stations and Zürich HB have the most *standing room only* departures.
- **Commuter tide:** departures from city hubs are crowded in the evening, departures from
  suburbs and border towns are crowded in the morning.
- When 2nd class has *standing room only*, 1st class still has many seats in about 3 of 4 cases.

## Contents

| Path | What it is |
|---|---|
| `notebooks/crowding_analysis.ipynb` | The analysis, with all charts |
| `app.py`, `views/` | Streamlit app (see below) |
| `crowding/parse.py` | Streaming parser for the SIRI-ET XML zip |
| `crowding/lines.py` | Line names (S12, IC5, …) from the GTFS timetable, matched on the train number |
| `crowding/build.py` | Downloads the data and builds the tables |
| `crowding/theme.py` | SDSC chart palette for matplotlib and plotly |
| `data/app/` | Small snapshot (7 days) that the app reads |

## App pages

- **Stations by hour:** map of crowded departures for each hour.
- **Crowded segments:** map of the stretches between stops, coloured by crowding, for each hour.
- **Commuter tide:** which stations are crowded in the morning and which in the evening.
- **A → B planner:** all direct trains between two stations, with the worst level on the way.
- **Station board:** departures of one station, with line, destination and level.
- **Line explorer:** heatmap (stop × hour) and Marey diagram (every train) for one line.
- **Busiest trains:** trains and lines with the most *standing room only* stops.
- **Next 3 months:** share of crowded departures for every forecast day.

## Run it

On Renku, open a session: the environment is built from `requirements.txt`.

Locally:

```bash
pip install -r requirements.txt
python -m crowding.build          # downloads ~420 MB (forecast + GTFS), parses 14 days (~2 min)
streamlit run app.py
```

`python -m crowding.build` also refreshes `data/app/`. Commit that folder to update the app.

## Data

- Occupancy forecast: SIRI-ET XML, one file per operator and day, updated daily.
  Levels: *many seats*, *few seats*, *standing room only*.
- Line names: [GTFS timetable](https://opentransportdata.swiss/en/dataset/timetable-2026-gtfs2020). The forecast has no
  line field, so the build matches each train number to its most frequent GTFS route (about 96% of departures match).
- Station coordinates: [service points](https://opentransportdata.swiss/en/dataset/service-point-v2) list.
  Stations outside Switzerland have no coordinates there, so the maps do not show them.

All three datasets are from [opentransportdata.swiss](https://opentransportdata.swiss) and are subject to its
[terms of use](https://opentransportdata.swiss/en/terms-of-use/).
