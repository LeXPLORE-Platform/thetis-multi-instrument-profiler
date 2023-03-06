# LéXPLORE Thetis

## Project Information

[LéXPLORE](https://lexplore.info) is research platform on Lake Geneva for a broad range of limnological research. The platform results from a collaboration between five partner institutions ([Eawag](https://www.eawag.ch/en/), [EPFL](https://www.epfl.ch/en/), [INRAE](https://www6.lyon-grenoble.inrae.fr/carrtel/), [UNIGE](https://unige.ch), [UNIL](https://www.unil.ch/index.html)). The LéXPLORE platform is anchored since February 2019 at a position reaching 110 m depth off the lake's north-shore.
The data presented here is part of the core dataset maintained by the technical team of LéXPLORE.
The data is used and displayed on the [Datalakes website](https://www.datalakes-eawag.ch/). Related data or products can be visualised and downloaded on the [Datalakes website](https://www.datalakes-eawag.ch/).

**References**:

Wüest, A., Bouffard, D., Guillard, J., Ibelings, B. W., Lavanchy, S., Perga, M. ‐E., & Pasche, N. (2021). LéXPLORE: a floating laboratory on Lake Geneva offering unique lake research opportunities. Wiley Interdisciplinary Reviews: Water, 8(5), e1544 (15 pp.). https://doi.org/10.1002/wat2.1544

Minaudo, C., Odermatt, D., Bouffard, D., Rahaghi, A. I., Lavanchy, S., & Wüest, A. (2021). The imprint of primary production on high-frequency profiles of lake optical properties. Environmental Science and Technology, 55(21), 14234-14244. https://doi.org/10.1021/acs.est.1c02585

See also the [360° virtual tour](https://www.eawag.ch/repository/lexplore/index.htm)


## Citation
Bouffard, D., Cunillera, G, Fillion, R., Gios, M., Guillard, J., Ibelings, B., Lavanchy, S., Minaudo, C., Miesen, F., Odermatt, D., Pasche, N., Perga, M-E., Plüss, M., Quetin, P., Rahaghi, A. I., Runnalls, J., Wüest, A. (2022). Data from Thetis CTD on LéXPLORE station, 2019 - 2022. DOI

DOI attribution pending.


## Sensors

The Thetis profiler consists of a suite of physical and bio-optical sensors mounted on a positively buoyant structure equipped with an onboard winch. Every three hours it collects a vertical profile of CTD (Conductivity, Temperature, and Depth), DO (Dissolved Oxygen) and PAR (Photosynthetic Active Radiation) data ranging from 0m to approx. 50m depth. The Thetis collects data during his ascent over from the park location (50 m depth) to the surface. An antenna that operates via FreeWave radio technology transfer the essential data when the profiler reaches the surface. Measurements period, rising speed and other characteristics can be updated remotely when the profiler is at the surface. Regular maintenances are carrid out to clean the optical sensors (See details in `notes` ). The Thetis is deployed 30 m away fromthe LéXPLORE platform (46°30’0.819″ N, 6°39’39.007″ E) Note that the deep parking location of the profiler minimize the biofouling. The Thetis profiler holds instruments that measure hyperspectral absorption and attenuation (WetLabs AC-S), scattering at 117° (at 440, 532, 630, 700 nm) and fluorescence by chlorophyll-a (EX/EM: 470/695 nm), colored dissolved organic matter (CDOM; EX/EM: 370/460 nm) with WetLabs ECO Triplets BBFL2W and BB3W, hyperspectral downwelling irradiance and upwelling radiance (Satlantic HOCRs), PAR radiation (WetLabs ECO PARS), conductivity, temperature, pressure (Sea-Bird CTD SBE49) and dissolved oxygen (Sea-Bird SBE63).  

### CTD
- **Brand, Model & SN**: Seabird, SBE 49, SN 49-0408
- **System integration**: Wetlab Thetis profiler
- **Accuracy**: Conductivity ± 0.0003 S/m, Temperature ± 0.002 °C, Pressure ± 0.1% FS
- **Setup** vertical resolution (assuming a standard 10cm/s rising speed): 0.55 cm

### DO
- **Brand, Model & SN**: Seabird, SBE 63, SN 63-1472
- **System integration**: Wetlab Thetis profiler
- **Accuracy**: 0.1 mg/L or ± 2%  
- **Setup** vertical resolution (assuming a standard 10cm/s rising speed): 10.6 m

### Hyperspectral absorption, attenuation
- **Brand, Model & SN**: WetLabs,  AC-S,  SN 286 or SN 380
- **System integration**: Wetlab Thetis profiler
- **Accuracy**: +- 0.01 m-1
- **Setup** Spectral resolution: 81 channels from 400 to 730 nm. Vertical resolution (assuming a standard 10cm/s rising speed): 2.2 m

### Scattering (3 wavelenghts). -part 1-
- **Brand, Model & SN**: Sea-Bird, ECO Triplet BB3W, SN 1076
- **System integration**: Wetlab Thetis profiler
- **Accuracy**: NA 
- **Setup**:  Scattering at 440 nm, 532 nm, 630 nm, measured at 117°. Vertical resolution (assuming a standard 10cm/s rising speed): 10 m

### Scattering (3 wavelenghts) -part 2-
- **Brand, Model & SN**: Sea-Bird, ECO Triplet BBFL2w, SN 1520
- **System integration**: Wetlab Thetis profiler
- **Accuracy**: NA 
- **Setup**:  Scattering at 700 nm, measured at 117°. Chlorophyll-a fluorescence (EX/EM: 470/695 nm). CDOM fluorescence (EX/EM: 370/460 nm). Vertical resolution (assuming a standard 10cm/s rising speed): 10 m

### Hyperspectral downwelling irradiance
- **Brand, Model & SN**: Satlantic, HOCR ICSW, SN 441
- **System integration**: Wetlab Thetis profiler
- **Accuracy**: 0.3 nm
- **Setup**:  180 channels from 300 to 1200 nm. Vertical resolution (assuming a standard 10cm/s rising speed): 10 m

### Hyperspectral upwelling radiance
- **Brand, Model & SN**: Satlantic, HOCR R08W, SN 557
- **System integration**: Wetlab Thetis profiler
- **Accuracy**: 0.3 nm
- **Setup**:  180 channels from 300 to 1200 nm. Vertical resolution (assuming a standard 10cm/s rising speed): 10 m

### Photosynthetically Active Radiation
- **Brand, Model & SN**: Sea-Bird, ECO PARs, SN 
- **System integration**: Wetlab Thetis profiler
- **Accuracy**: NA 
- **Setup**:  integration from 400 to 700 nm. Vertical resolution (assuming a standard 10cm/s rising speed): 10 m


## Installation

:warning You need to have [git](https://git-scm.com/downloads) and [git-lfs](https://git-lfs.github.com/) installed in order to successfully clone the repository.

- Clone the repository to your local machine using the command: 

 `git clone https://renkulab.io/gitlab/lexplore/thetis.git`
 
 Note that the repository will be copied to your current working directory.

- Use Python 3 and install the requirements with:

 `pip install -r requirements.txt`

 The python version can be checked by running the command `python --version`. In case python is not installed or only an older version of it, it is recommend to install python through the anaconda distribution which can be downloaded [here](https://www.anaconda.com/products/individual). 

## Usage

### Process new data

In order to process new data locally on your machine the file path needs to be adapted to your local file system. The following steps are therefore necessary: 

- Edit the `scripts/input_batch.bat` file. Change all the directory paths to match your local file system. This file contains all the file paths necessary to launch the batch scripts `runfile.bat`.

- Edit the `scripts/input_python.py` file. Change all the directory paths to match your local file system. This file contains all the directories where the python script outputs data to.

To process new data, place the data in the input directory which you specified in the `scripts/input_batch.bat` file. Double-clicking on the `runfile.bat` file will automatically 
process all the data in the input directory and store the output in the directories specified in the `scripts/input_python.py` file. 

### Adapt/Extend data processing piepeline

The python script `scripts/main_thetis.py` defines the different processing steps while the python script `scripts/thetis.py` contains the python class thetis with all the corresponding 
class methods to process the data. To add a new processing or visualization step, a new class method can be created in the `thetis.py` file and the step can be added in `main_theits.py` file.
Both above mentioned python scripts are independent of the local file system.

#### Full Resolution data

The live data provided by the thetis profiler is decimated. It can be replaced by the full resolution data once it is available. In order to do so, the variable `full_resolution` 
in the python script `scripts/main_thetis.py` needs to be set to `True` before processing the data. Don't forget to set it back to `False` after having processed the full_resolution data. 


## Data

The data can be found in the folder `data`. The data is structured as follows:

### Data Structure

- **Level 0**: Raw data collected from the different sensors.

- **Level 1A**: Raw data stored to NetCDF file where attributes (such as sensors used, units, description of data, etc.) are added to the data.

- **Level 1B**: Column with quality flags are added to the Level 1A data. Quality flag "1" indicates that the data point didn't pass the 
quality checks and further investigation is needed, quality flag "0" indicates that no further investiagion is needed.

- **Level 2**: The data is gridded into a vertical and temporal grid with a vertical spacing of 0.1m for the CTD data and 1.0m for the DO and PAR data. The temporal spacing of the grid is 3h and the data of a profile (which is recorded over approx. a time period of 10 minutes) is set to one common timestamp. 


## Quality assurance

Quality checks include but are not limited to range validation, data type checking and flagging missing data.

###  Events 

Maintenance dates, interesting or surprising events, non identified by the quality assurance outliers are listed in the folder `events`. coming soon
Check also the `sensor_history` (if existing)

## Collaborators

- **Concept, finances, project management** Damien Bouffard, Jean Guillard, Bas Ibelings, Natacha Pasche, Marie-Elodie Perga, Alfred Wüest   
- **Installation, maintenance, data collection** Guillaume Cunillera, Roxane Fillion, Matteo Gios, Sébastien Lavanchy, Floreana Miesen, Michael Plüss, Philippe Quetin 
- **Data pipeline** Camille Minaudo, Daniel Odermatt, Abolfazl Irani Rahaghi, James Runnalls
- **Data review** Damien Bouffard
- **Contact tech** Sébastien Lavanchy 
- **Contact science** Damien Bouffard

