# covid-19-risk-map
Data, methods, and code to develop Global Corona Virus (COVID19) risk maps. Work in progress.

![](images/zoomed-risk-map.png)

# Disclaimer
This is a very simple methodology to assess hazard risks from COVID-19 in a geographical manner. 
It is by no means accurate and the users should be aware of the simplification in the procedures and therefore it needs to be used with care.

Ideally, it should be reviewed by data scientists, geographical epidemiologists, other health professionals, and policymakers to be adjusted for gaining some overall insights into the pandemic.

# The Logic

The logic is relatively simple and relies on the hazard risk approach. In the hazards research it is usually accepted that the `hazard risk = hazard magnitude x vulnerability` [1].

The hazard magnitude is known up to a certain extent, and it is estimated to be some function of the current confirmed cases, deaths and recovered cases. The vulnerability, on the other hand, can be defined by the number of people that is vulnerable to the disease, and it is some function of the population.

For the hazard component, the confirmed cases and deaths collected across the world are used [2]. For the vulnerability component, a 1km population grid is used [3]. The population grid is already downloaded, aggregated to 10 km resolution and included it in the repository [(ppp_2020_10km_Aggregated.zip)](ppp_2020_10km_Aggregated.zip)

The main logic is the following: Multiplication of confirmed cases and the population gives one risk measure (a). But since testing is not uniform across the world and the number of deaths might be more reliable, death numbers are multiplied with the population for the second risk component (b). Finally, the larger the population is, the more risk it has at an exponential level even if there are no confirmed cases yet. That is why the population was squared to generate the third risk component (c).

In the program, each risk component is scaled between 0 and 1000, followed by the calculation below:

`total risk = a + b + c/2`

This is a first attempt to quantify the risk and it is acknowledged that countless factors should ideally go into this mapping (e.g. temperatures, connectivity and human flows, existing policies, type of medical system, economics, level of social isolation, etc.).

# Flow of the program

1. The program reads all the constants and file names from the [covConst.py](covConst.py) file. The outcome of the program can be changed simply by changing the variables (such as the size of the low pass filter).
2. The program [covid19RiskMap.py](covid19RiskMap.py) pulls the COVID 19 data from the COVID-19 (2019-nCoV) Data Repository by Johns Hopkins CSSE [2].
3. Then it creates a shapefile containing the confirmed cases and deaths with their lat/long.
4. Then it creates two rasters for both confirmed cases and deaths.
5. Because the rasters are created with a relatively fine spatial resolution, a low pass filter using a Gaussian kernel was applied on to these rasters for a more meaningful spatial distribution (basically distribute the confirmed cases and deaths to neighboring pixels).
6. During this process, the geographical references disappear so they had to be reassigned.
7. The program adjusts the size of the population grid since the raster calculation is done by numpy, which means the arrays need to be in identical size.
8. Each raster is read into a numpy array, and the calculations described above are carried out.
9. The result is saved as a raster named “covid-risk.tif”.

# Setup
The script is written in Python, and it can be run as simple as the following command after everything else is set up:

`python covid19RiskMap.py`

There is a large number of libraries used by the script, and they need to be installed either by conda or pip. Interested parties are encouraged to install [conda/Anaconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) and set up an environment using the following commands and the [covid-env.txt](covid-env.txt) file included in the repo. This should be the easiest setup.

`conda create --name covid --file covid-env.txt`

This command should download all the necessary libraries required to run the script.

Finally, run the following to obtain the “covid-risk.tif” file which includes geographic coordinates:

`python covid19RiskMap.py`

### Note
It seems like the package "wget" needs to be installed using pip due to some version related issues

`pip install wget`

# Visualization

For the screenshots, ArcGIS Pro was used, but an open-source solution like QGIS can be easily deployed, as well.  The final solution might include a capability of visualization on Jupyter Notebooks. Ideally, the user would be able to zoom into portions of the final map on their browser.

![](images/covid-19-risk-map.png)

# References and Sources
1. Blong, R. J. "Volcanic hazards risk assessment." Monitoring and mitigation of volcano hazards. Springer, Berlin, Heidelberg, 1996. 675-698.
2. https://github.com/CSSEGISandData/COVID-19
3. Lloyd, C., Sorichetta, A. & Tatem, A. High resolution global gridded data for use in population studies. Sci Data 4, 170001 (2017). https://doi.org/10.1038/sdata.2017.1

# License

Copyright 2020 Naci Dilekli

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
