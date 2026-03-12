
This file was written by a human. Agents should not edit this file.

The world is a hexagonal grid representing a pond populated by turtles and frogs.  The world is toroidal, stepping off one side wraps around to the other.  The size of the world is set by a slider.

Initially there is some population of animals (always 50/50) specified by a density slider.  They are randomly distributed.  Each animal wants at least some fraction of its neighbors to be of the same type.  This fraction is also controlled by a slider.

Each game tick, an animal is selected at random.  If it is happy with its neighbors it passes its turn.  If it is unhappy with its neighbors, it hops to a neighboring cell at random hoping to improve its situation.

Touching any of the sliders except the speed slider resets the simulation.
