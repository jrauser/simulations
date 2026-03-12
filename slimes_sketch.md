This file was written by a human.  Agents should not edit this file.

This simulation is of slime mold aggregation.  As usual the world is a hexagonal grid with toroidal shape, stepping off one edge wraps around to the opposite side. 

There is a population of slime molds.  Each cell in the world can hold only one slime.   Each game epoch, each slime gets to act in random order.  When it is a slime's turn it emits one unit of pheromone.  If a slime is on a patch that has a pheromone concentration above some threshold (default 2), it samples it's neighboring cells and moves to the one with the highest amount of pheromone and is empty.  If all neighboring cells are occupied, it does not move.  If the slime is on a patch whose concentration of pheromone is below the threshold is move to a random empty neighboring patch.

Pheromone evaperates (by 10% per game epoch).  Pheromone also diffuses to neighboring patches each epoch.  Not sure by how much.

Sliders control population, pheromone drop, seeking threshold, evaporation rate, diffusion rate and speed.  Touching any slider except the speed slider resets the simulation.