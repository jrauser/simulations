
This file was written by a human and should not be edited by agents.

Termites is a toy simulation inspired by Resnik's book.

# The arena

A hexagonal grid of cells. Flat top. Cube coordinates. The arena is toroidal, stepping off on edge wraps around to the opposite side. The size will be configurable. 

The arena is populated by wood chips and termites. Initially they are distributed randomly. The density of each will be configurable. 

An epoch is one round where each termite gets a move. Termite moves are ordered randomly each epoch. 

# Termites

Termites have two states: either carrying a woodchip or emptyhanded.

When a termite is emptyhanded they take a step in a random direction.  Multiple termites can occupy a grid cell without issue.  If there is a woodchip in their new cell they pick it up.

When a termite is carrying a woodchip there are two possibilities.  First, if their current cell also has a woodchip, they drop their chip in a neighboring empty (no woodchip) cell.  Second, if there are no empty cells they retain their chip.  If their current cell does not have a woodchip they take a random step.

# Rendering

The background should be dark.  Chips should be tan.  A termite carrying a chip should be reddish.  An emptyhanded termite should be blue.

There should be the following controls:
* a slider for the size of the arena
* a slider for initial termite density
* a slider for initial woodchip density
* a slider for simulation speed 

Touching any of the sliders except the speed control resets the simulation.

# Technical details

I think pygame is a good library for this project, but if you have other ideas that's fine.

Since this is a toy simualtion, all the code in single file is probably fine.  There should probably be classes for Arena and Termite.  Rendering code and simulation state code should be kept strictly separate.

I don't think writing tests is important, though if it were me I'd definitely write tests around coordinate handling, as that's error prone for humans.

The code should pass normal linters (pyflake or ruff) without complaint.
