# MSXVI Strategy
## About
This repository contains the work of the Midnight Sun ~~Strategy team~~, including code for setting up and interacting with a simulator and optimization algorithms.

## FSGP & ASC
FSGP serves as a qualifying event for ASC. 

    Scoring is based on the highest overall official distance driven or laps completed over the duration of the event with ties being broken by the lowest overall official elapsed time or fastest lap" in other words maximising distance for a fixed time. 

If qualified, the objectives of ASC are the following:

    1. To complete the American Solar Challenge base route without trailering.
    2. To complete as many official miles as possible. (1st Tiebreaker)
    3. To complete the distance in the shortest elapsed time. (2nd Tiebreaker)

Successfully achieving these objectives hinges on two factors: 
- designing an efficient solar car (less power out)
- following an optimal race strategy

Race strategy boils down to a single question:

### **What speed should we drive at?**

We address this question by leveraging the route, weather, and solar irradiance data. 

## Simulator
Still deciding how this will be implemented... Will either be done with simulink or custom python models (leaning towards this right now)

## Optimizer
Intended to optimize velocity based on the simulation model. Planning on using Scipy for this. What about Z3 prover? Well from my research it seems to be more suited towards answering 


![](docs/architecture.svg)