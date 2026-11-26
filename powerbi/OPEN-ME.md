# Opening the Power BI report

`CanberraPlaygrounds.pbip` is a Power BI Project: the report (`CanberraPlaygrounds.Report`, PBIR format) and the semantic model (`CanberraPlaygrounds.SemanticModel`, TMDL) saved as text, so the repo can show every change. Power BI Desktop opens it like a `.pbix`.

## What you need

- Power BI Desktop for Windows, a recent version (2026). Projects and the PBIR report format are standard in current versions. If Desktop is older than about mid 2025, turn on **File, Options and settings, Options, Preview features, Power BI Project (.pbip) save option** and **Store reports using enhanced metadata format (PBIR)**, then restart Desktop.
- The repo folder on the Windows machine. In Parallels the Mac home folder is usually shared as `\\Mac\Home`.

## Open it

1. In Windows, go to the repo's `powerbi` folder and double-click `CanberraPlaygrounds.pbip`, or in Desktop use **File, Open report, Browse reports** with the file type set to *Power BI project files (\*.pbip)*.
2. The visuals are empty the first time. Select **Refresh** on the Home ribbon.
   - By default the data is read from the repo's public copy on GitHub (`DataFolder` is `https://raw.githubusercontent.com/cjmuldoon/plotlay-canberra-playgrounds/main/data/`). If Desktop asks how to connect, choose **Anonymous** and then **Connect**.
   - To read the files from disk instead, go to **Home, Transform data, Edit parameters** and set `DataFolder` to the full path of the repo's `data` folder, **ending with a backslash** (for example `\\Mac\Home\plotlay-canberra-playgrounds\data`). Then select **OK** and **Apply changes**.
   - If Desktop warns about privacy levels, choose **Ignore privacy levels** (all the sources are public open data).
3. Check the numbers (below).

If the report was updated while open, close Power BI and reopen the .pbip rather than using Apply external changes.

## Check the numbers after Refresh

After **Refresh**, on **Canberra** (as the report opens):

| Card | Should read |
|---|---|
| Within a 5-minute walk | 49.4% |
| Inside a 400 m circle | 81.7% |
| Children within the walk | 40,907 |
| Children 0 to 14 | 82,789 |

South Canberra is the lowest district in the bar chart (24.5%). On **Suburbs**, Kingston is the lowest bar; on **Playgrounds**, the card reads 537.

## The model

- **MeshBlocks**: one row per mesh block with residents (ABS 2021, `data/tables/meshblocks.csv`): its suburb and district, dwellings, residents and children aged 0 to 14 (residents times the SA1's share aged 0 to 14), its street length, how much of it is within a 5-minute walk of a playground, within 400 m in a straight line and within a 10-minute walk, the children counted within each, and a point inside it (`lat`, `lng`). Measures: `All children`, `Children within the walk`, `Share within the walk`, `Share as the crow flies`, `Share within 10 minutes`, `Mesh block count`.
- **Districts**: one row per district (`districts.csv`), related to MeshBlocks by `district`.
- **Suburbs**: one row per suburb (`suburbs.csv`), with `compared` = yes for the suburbs with 300 children or more. Measures: `Suburb share within the walk`, `Suburb share as the crow flies`.
- **Playgrounds**: one row per playground (`playgrounds.csv`): name, kind, shade, suburb, soft fall area and the street length within its own 5-minute walk. Measure: `Playground count`.

## The maps

- **Azure Maps** (pages 1 and 3): a point inside every mesh block, coloured by how much of its streets is within the walk (`walk_band`), and the playgrounds by kind. Canberra has 4,344 mesh blocks with residents, more than the roughly 1,500 places a Shape Map draws; the filled map is in the README and on the showcase page. Azure Maps needs to be allowed in your tenant (**File, Options and settings, Options, Security, Map and filled map visuals**); if it is off, the maps show as blank and the other visuals still work.

## Save a .pbix too

After the refresh, use **File, Save as** with the type **Power BI file (\*.pbix)** to save `powerbi\CanberraPlaygrounds.pbix`. It includes the data, so it opens without a refresh.

## Publish (only if you choose to)

Use **Home, Publish**. In the Power BI service, set the semantic model's **Data source credentials** for the GitHub address to **Anonymous**. Scheduled refresh then works with no gateway. **Publish to web** makes a public link, so only use it if you mean the report to be public.

## Shot list for the website and the video

| # | Shot | How | Length |
|---|---|---|---|
| 1 | Canberra | As it opens; hover a mesh block in Kingston | still |
| 2 | Suburbs | As it opens | still |
| 3 | Playgrounds | As it opens | still |

Save page images into `powerbi/Screenshots/` (a PDF export of all pages is fine too).
