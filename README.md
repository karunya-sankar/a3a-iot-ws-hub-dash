# A3a: Websockets-based Hub Dashboard Simulation of local IoT system

NOTE: you can view this Markdown (.md) file in the correct formatting using the "preview button" in the top-right corner in Visual Studio Code.

## Overview

Basically, this homework shows you the basics of a local (home) IoT
system, except everything runs locally on your computer since we have
not yet quite gotten to making the Bluetooth Low Energy edge node itself.
This system has three processes, one to simulate each component of
a local IoT system: an edge node process(es), a home hub process,
and finally, a user (your phone or computer) client process.  We do
not have the cloud portion in this simulation yet, but will add it
in the not-so-distant future.

## System block diagram

![System block diagram](system_diagram.png)

## Packages required

First, make sure to install:
1. `psutil` via Miniforge Prompt and the ee5450 env: `mamba install psutil` so that we can 
do the scans for "service discovery".  
1. Insomnia via: https://insomnia.rest/download

Normally you'd use bleak or whatever Bluetooth Low Energy service 
discovery tool, but since we haven't quite yet gotten to that yet, 
we'll use `psutil` to discover services on our own computer.  The 
simulator below will run different services that provide sensor data 
on different TCP ports above 8080 in order to simulate the discovery 
process.  The Hub ingester and dashboard work together to get data 
from the sensor nodes processed and displayed for the homeowner. This 
setup essentially allows us to simulate a whole local home IoT system 
on your computer.

Insomnia allows us to test HTTP and WebSockets services without having
to keep refreshing on the web browser.  You could also just use `aiohttp`
directly with Python unit tests as well, but it's nice to have some 
exposure to simpler tools that require less work on your end.  Of course,
if you were working in industry and trying to make a reliable system
instead of just trying to finish your homework in a couple of weeks

## System components

Here are the different programs that are in this folder:

App hub client allows us to chose which node to connect to and to do scans

App iot node simulator runs websockets servers on different ports

Hub dashboard creates means (averages) of whatever data is ingested

Hub ingester is websockets client to simulate BLE client

## Tasks TODO

It is up to you to create the following improvements to the system:
    1. sdfsefdsf
    1. ssdafsdfa
    1. asdfsdfds
