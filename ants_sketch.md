
Let's do another one simulating an ant colony.  This time I want to use the ideas of Resnik's starlogo.  In starlogo there are two high level entities, the turtles and patches.  That is, the environment is composed of a set of patch objects, each of which get a chance to act every turn.  The patches and communicate with each other, for example diffusing a chemical to other patches.  The turtles can also make inquiries about patches.  

# The world

The world is composed of a hexagonal grid of patches.  At the center is the ant colony.  The size of the world should be roughly the typical foraging range of an ant.  The grid's resolution (patch size) should be small enough that the world feels roughly continuous.  These numbers are to be determined.

The world initially contains small clumps of food.  Food can be carried to the colony by ants.

# Ants

The colony contains a number of ants.  Some fraction of them (perhaps half?) can leave the colony to find food.  Ants outside the colony have three behaviors.

## Exploration

First, they can explore randomly.  Ants always know where the colony is, returning home is no problem.  But ants do not always take the fastest route.  When an ant is within some small distance to food it can detect the food and head directly for it.  Similarly, an ant can detect pheromone and switch to following (see below).

## Carrying food home

Second, when an ant is adjacent to a cell with food, they pick up some food and return home (again taking random steps with some probability).  When returning home, they drop a pheromone at each step, leaving a trail that other ants can follow.

## Following

Upon detecting pheromone, ants move along a decreasing gradient of pheromone strength. 

## A note on navigation

There is some chance that when navigating home, toward food, or following pheromone gradient, they take a random step.  I think this will make the simultion visually more interesting. 

# Patches

Each patch (grid cell) contains an amount of pheromone.  Each simulation step, the pheromone decays (exponentially?).  This creastes a gradient of pheromone that ants can follow.

Patches that contain food have a counter of how much food is left.  Food is depleted by any visits.  By default, let's have food deplted after 10 visits.

# Rendering

Render the grid with a flat top.  Ants outside the colony should be colored according to their state.  Pheremone strength should be visible.  Depleted food should also be visible, but a darker color than active food sources.

I'd like sliders that control ant population, number of food clusters, and simulation speed.  Touching any slider except the speed slider resets the simulation.

