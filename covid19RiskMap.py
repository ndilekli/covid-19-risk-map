import pandas as pd
import numpy as np

from scipy import fftpack, ndimage
import scipy.stats as st
import imageio
from PIL import Image, ImageDraw
import os, wget
from zipfile import ZipFile

### Load geo libraries
import geopandas as gpd
from shapely.geometry import Point, Polygon
from osgeo import gdal, gdal_array, osr, ogr

### Load constants
import covConst

def unzipFile(file):
    with ZipFile(file, 'r') as zipObj:
        # Extract all the contents of zip file in different directory
        zipObj.extractall()

# Using https://github.com/imdevskp/covid_19_jhu_data_web_scrap_and_cleaning, with slight modifications
def getCovidData():
    print(os.getcwd())
    # First get rid of all existing csv files
    for item in os.listdir(os.getcwd()):
        if item.endswith(".csv"):
            os.remove(os.path.join(os.getcwd(), item))

    # Get 2019 Novel Coronavirus COVID-19 (2019-nCoV) Data Repository by Johns Hopkins CSSE
    urls = ['https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Confirmed.csv', 
        'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Deaths.csv', 
        'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Recovered.csv']

    for url in urls:
        filename = wget.download(url)

    # datasets
    # --------
    conf_df = pd.read_csv('time_series_19-covid-Confirmed.csv')
    deaths_df = pd.read_csv('time_series_19-covid-Deaths.csv')
    recv_df = pd.read_csv('time_series_19-covid-Recovered.csv')

    dates = conf_df.columns[4:]
    conf_df_long = conf_df.melt(id_vars=['Province/State', 'Country/Region', 'Lat', 'Long'], 
                                value_vars=dates, var_name='Date', value_name='Confirmed')
    deaths_df_long = deaths_df.melt(id_vars=['Province/State', 'Country/Region', 'Lat', 'Long'], 
                                value_vars=dates, var_name='Date', value_name='Deaths')
    recv_df_long = recv_df.melt(id_vars=['Province/State', 'Country/Region', 'Lat', 'Long'], 
                                value_vars=dates, var_name='Date', value_name='Recovered')
    full_table = pd.concat([conf_df_long, deaths_df_long['Deaths'], recv_df_long['Recovered']], 
                        axis=1, sort=False)
    # full_table.head()    
    # removing county wise data to avoid double counting
    full_table = full_table[full_table['Province/State'].str.contains(',')!=True]
    full_table.to_csv('covid_19_clean_complete.csv', index=False)

# Gaussian kernel
# https://stackoverflow.com/questions/29731726/how-to-calculate-a-gaussian-kernel-matrix-efficiently-in-numpy
def gkern(kernlen=10, nsig=3):
    """Returns a 2D Gaussian kernel."""

    x = np.linspace(-nsig, nsig, kernlen+1)
    kern1d = np.diff(st.norm.cdf(x))
    kern2d = np.outer(kern1d, kern1d)
    return kern2d/kern2d.sum()

def csv2shp(csvFile, shpFile):
    # Load Dataset
    df = pd.read_csv("covid_19_clean_complete.csv")

    # Get first 5 records
    # print("The head: ", df.head())

    # List columns
    # print("Columns: ", df.columns)

    # Rename columns for shapefile
    df.rename(columns={'Province/State':'Province_State','Country/Region':'Country_Region'},inplace=True)

    # Get the dimensions / shape of the df
    # print("Shape of the dataframe:", df.shape)

    # Print the datatypes of each column
    # print("Datatypes:", df.dtypes)

    # Convert Data to GeoDataframe
    gdf = gpd.GeoDataFrame(df,geometry=gpd.points_from_xy(df['Long'],df['Lat']))

    # Print head of gdf
    # print("Head of gdf", gdf.head())

    gdf.to_file(driver = 'ESRI Shapefile', filename= shpFile)

    ds = None
    gdf = None

def shp2ras(shpFile, attr, rawRaster, pixelSize, noDataValue, x_min, y_min, x_max, y_max):
    # Used the following link as a guideline
    # https://pcjericks.github.io/py-gdalogr-cookbook/raster_layers.html
    # Define pixel_size and NoData value of new raster

    # I think I might need to use the Pop Grid 
    pixel_size = 0.083333333
    NoData_value = -9999

    # Open the data source and read in the extent
    source_ds = ogr.Open(shpFile)

    source_layer = source_ds.GetLayer()
    # x_min, x_max, y_min, y_max = source_layer.GetExtent()
    # y_max = 83
    # y_min = -72
    # x_min = -180
     #x_max = 180

    # Create the destination data source
    x_res = int((x_max - x_min) / pixel_size)
    y_res = int((y_max - y_min) / pixel_size)

    # I changed from GDT_Byte to GDT_UInt32 to make it work
    target_ds = gdal.GetDriverByName('GTiff').Create(rawRaster, x_res, y_res, 1, gdal.GDT_UInt32)
    target_ds.SetGeoTransform((x_min, pixel_size, 0, y_max, 0, -pixel_size))
    band = target_ds.GetRasterBand(1)
    band.SetNoDataValue(NoData_value)

    # How to set the spatial reference: https://gis.stackexchange.com/questions/82031/gdal-python-set-projection-of-a-raster-not-working
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    target_ds.SetProjection(srs.ExportToWkt())

    # print("ATTRIBUTE=" + attr)

    gdal.RasterizeLayer(target_ds, [1], source_layer, options=["ATTRIBUTE=" + attr, "ALL_TOUCHED=TRUE"])

    source_ds = None
    target_ds = None

# Convert shape to raster and implement 
def rasLowPass(inRas, outRas, kernlen, nsig, multiplier):
    # https://stackoverflow.com/questions/7569553/working-with-tiffs-import-export-in-python-using-numpy
    im = Image.open(inRas)

    # https://stackoverflow.com/questions/6094957/high-pass-filter-for-image-processing-in-python-by-using-scipy-numpy

    #convert image to numpy array
    image1_np=np.array(im)

    # print("Raw image max", image1_np.max())

    # https://docs.scipy.org/doc/numpy/reference/generated/numpy.ones.html
    kernel = gkern(kernlen, nsig) * multiplier

    lowpass = ndimage.convolve(image1_np, kernel)
    # print("Lowpass max", lowpass.max())
    return lowpass

# Convert np array to georeferenced raster
# https://pcjericks.github.io/py-gdalogr-cookbook/raster_layers.html
def array2raster(newRasterfn,originX, originY,pixelSize,array):
    from osgeo import osr
    cols = array.shape[1]
    rows = array.shape[0]
    reversed_arr = array[::-1] # reverse array so the tif looks like the array

    driver = gdal.GetDriverByName('GTiff')
    outRaster = driver.Create(newRasterfn, cols, rows, 1, gdal.GDT_UInt32)
    outRaster.SetGeoTransform((originX, pixelSize, 0, originY, 0, pixelSize))
    outband = outRaster.GetRasterBand(1)
    outband.WriteArray(reversed_arr)
    outRasterSRS = osr.SpatialReference()
    outRasterSRS.ImportFromEPSG(4326)
    outRaster.SetProjection(outRasterSRS.ExportToWkt())
    outband.FlushCache()

# https://github.com/jgomezdans/eoldas_ng_observations/blob/master/eoldas_ng_observations/eoldas_observation_helpers.py
# Changed it so that it will save to GTiff with a specified output name
def reproject_image_to_master ( master, slave, out, res=None ):
    """This function reprojects an image (``slave``) to
    match the extent, resolution and projection of another
    (``master``) using GDAL. The newly reprojected image
    is a GDAL VRT file for efficiency. A different spatial
    resolution can be chosen by specifyign the optional
    ``res`` parameter. The function returns the new file's
    name.
    Parameters
    -------------
    master: str 
        A filename (with full path if required) with the 
        master image (that that will be taken as a reference)
    slave: str 
        A filename (with path if needed) with the image
        that will be reprojected
    res: float, optional
        The desired output spatial resolution, if different 
        to the one in ``master``.
    Returns
    ----------
    The reprojected filename
    TODO Have a way of controlling output filename
    """
    slave_ds = gdal.Open( slave )

    slave_proj = slave_ds.GetProjection()
    slave_geotrans = slave_ds.GetGeoTransform()
    data_type = slave_ds.GetRasterBand(1).DataType
    n_bands = slave_ds.RasterCount

    master_ds = gdal.Open( master )

    master_proj = master_ds.GetProjection()
    master_geotrans = master_ds.GetGeoTransform()
    w = master_ds.RasterXSize
    h = master_ds.RasterYSize
    #if res is not None:
    #    master_geotrans[1] = float( res )
    #    master_geotrans[-1] = - float ( res )

    # dst_filename = slave.replace( ".tif", "_crop.vrt" )
    dst_ds = gdal.GetDriverByName('GTiff').Create(out,
                                                w, h, n_bands, data_type)
    dst_ds.SetGeoTransform( master_geotrans )
    dst_ds.SetProjection( master_proj)
    dst_ds.GetRasterBand(1).SetNoDataValue(0)

    gdal.ReprojectImage( slave_ds, dst_ds, slave_proj, master_proj, gdal.GRA_NearestNeighbour)
    dst_ds = None  # Flush to disk
    return out

# Convert the first band of a raster to a simple python array for raster calculations
def raster2array(raster):
    ds = gdal.Open(raster)
    b = ds.GetRasterBand(1)
    arr = b.ReadAsArray()
    return arr

# Main operations
def main():
    # Unzip the population grid
    unzipFile(covConst.ppp_2020_10km_aggregated_zip)

    # Get the Covid-19 data online
    getCovidData()

    # Convert the csv file into a shapefile
    csv2shp(covConst.csvFile, covConst.shpFile)

    # Rasterize the shp file
    shp2ras(covConst.shpFile, "Confirmed", covConst.corConfirmed, covConst.pixelSize, covConst.noDataValue, covConst.x_min, covConst.y_min, covConst.x_max, covConst.y_max)
    
    # Implement a low pass for local spread risk
    lowpassConfirmed = rasLowPass(covConst.corConfirmed, covConst.corConfirmed_LP, covConst.kernlen, covConst.nsig, covConst.multiplier)
    # Georeference the image with the low pass
    array2raster(covConst.corConfirmed_LP_georef, covConst.x_min, covConst.y_min, covConst.pixelSize, lowpassConfirmed)
    # Align the pop grid to the corona grid(s)
    reproject_image_to_master(covConst.corConfirmed_LP_georef, covConst.ppp_2020_10km_aggregated, covConst.ppp_2020_10km_aggregated_aligned)

    # Create the "Deaths" raster
    shp2ras(covConst.shpFile, "Deaths", covConst.corDeaths, covConst.pixelSize, covConst.noDataValue, covConst.x_min, covConst.y_min, covConst.x_max, covConst.y_max)
    
    # Implement a low pass for the "Confirmed" raster  for local spread risk
    lowpassDeaths = rasLowPass(covConst.corDeaths, covConst.corDeaths_LP, covConst.kernlen, covConst.nsig, covConst.multiplier)

    # Georeference the the "Confirmed" raster with the low pass
    array2raster(covConst.corDeaths_LP_georef, covConst.x_min, covConst.y_min, covConst.pixelSize, lowpassDeaths)

    # Raster to array
    pop_arr = raster2array(covConst.ppp_2020_10km_aggregated_aligned)
    confirmed_arr = raster2array(covConst.corConfirmed_LP_georef)
    deaths_arr = raster2array(covConst.corDeaths_LP_georef)

    # apply equation
    par1 = confirmed_arr*pop_arr
    par1_std = np.interp(par1, (par1.min(), par1.max()), (0, 1000))

    par2 = deaths_arr*pop_arr
    par2_std = np.interp(par2, (par2.min(), par2.max()), (0, 1000))

    par3 = pop_arr**2
    par3_std = np.interp(par3, (par3.min(), par3.max()), (0, 1000))

    raster_calculation = par1_std + par2_std + par3_std / 2

    # print("Max values of each parameter", par1_std.max(), par2_std.max(), par3_std.max())

    # save array, using corConfirmed_LP_georef as a prototype
    gdal_array.SaveArray(raster_calculation.astype("float32"), covConst.output, "GTIFF", covConst.corConfirmed_LP_georef)

if __name__ == "__main__":
    main()
    
    