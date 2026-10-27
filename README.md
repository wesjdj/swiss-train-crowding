# Swiss train crowding forecast

When and where are Swiss trains crowded? This project uses the SBB
[Occupancy Forecast SIRI Dataset](https://opendata.swiss/en/dataset/occupancy-forecast-siri-dataset)
from opendata.swiss. The dataset gives the expected occupancy of SBB, BLS, Thurbo, SOB and
Zentralbahn trains for the next three months, for each stop and each class.

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
| `app.py` | Streamlit app: map by hour, station board, busiest trains, commuter tide, 3-month calendar |
| `crowding/parse.py` | Streaming parser for the SIRI-ET XML zip |
| `crowding/build.py` | Downloads the data and builds the tables |
| `crowding/theme.py` | SDSC chart palette for matplotlib and plotly |
| `data/app/` | Small snapshot (7 days) that the app reads |

## Run it

On Renku, open a session: the environment is built from `requirements.txt`.

Locally:

```bash
pip install -r requirements.txt
python -m crowding.build          # downloads ~130 MB, parses 14 days (~2 min)
streamlit run app.py
```

`python -m crowding.build` also refreshes `data/app/`. Commit that folder to update the app.

## Data

- Occupancy forecast: SIRI-ET XML, one file per operator and day, updated daily.
  Levels: *many seats*, *few seats*, *standing room only*.
- Station coordinates: [service points](https://opentransportdata.swiss/en/dataset/service-point-v2) list.
  Stations outside Switzerland have no coordinates there, so the maps do not show them.

Both datasets are from [opentransportdata.swiss](https://opentransportdata.swiss) and are subject to its
[terms of use](https://opentransportdata.swiss/en/terms-of-use/).
