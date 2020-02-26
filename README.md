# OpenTripPlanner server for Python

This package uses OpenTripPlanner to run network analysis such as shortest path, Catchment isochrone, and Origin-Destination Matrix. It requires an OTP server running locally on your machine. 

Below briefly explains how to set up OTP, and how to use the scripts.

---

## Setting up OTP server

To use OTP API it is necessary to setup OTP server. Here is a guide:

### Install Java
OTP is written in Java. It is necessary to install download and install 64-bit Java Runtime Environment (not 32-bit). This can be downloaded here: 

```
https://java.com/en/download/manual.jsp
```

### Download OTP

The OTP can be downloaded in the executable .jar file format. The version I used for this repo is ```otp-1.3.0-shaded.jar```. This can be downloaded here: 

```
https://repo1.maven.org/maven2/org/opentripplanner/otp
```

### Download network files

To use OTP for PT network analysis we need an Open Street Map (OSM) file of the street network and a General Transit Feed Specification (GTFS) for the PT data. 

The OSM can be downloaded from: 

```
https://www.openstreetmap.org
```

The GTFS can be downloaded from: 

```
https://transitfeeds.com
```
---

## Running the OTP server

To run the OTP sever, put the OSM, GTFS and OTP .jar files into a folder (e.g. ```D:\otp```) and use the following commands to build a routable graph.

```shell
java -Xmx4G -jar otp-1.3.0-shaded.jar --build D:\otp --inMemory
```

The ```4``` in the ```-Xmx4G``` refers to how much memory should be allocated to the build.

Check out ```http://localhost:8080/``` to test if it's routing properly.

---

## Running the Scripts
Now you can open Python and start using the scripts. First import the package ```{.sourceCode .python}import pyotp as otp```  There are four functions in my script:

1) route: This function allows to find the best route between a pair of locations. Supported modes include CAR, BUS, FERRY, RAIL, TRANSIT, WALK, BICYCLE. You can use a combination of modes.

2) service_area: This function creates an isochrone of the catchment area for any points on the network. 

3) od_matrix: This function creates a matrix of origin-destination routes. 

An example for each of these functions can be found in ```ipynb/examples.ipynb```

---

## Notes
* This package is experimental.
* There are no tests written yet.
* I welcome contributions from anyone and everyone.

---

## Authors
* Saeid Adli, 2019/01/24
