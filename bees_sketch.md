This file was written by a human.  Agents should not edit this file.

# Initial sketch

The world is one square kilometer.  Time progresses in steps of N seconds (maybe 5?).  After each step, actors in the world get a chance to update their behavior.

There is a bee hive in the center of the world. The has a population of worker bees of some size (what's normal for a bee hive?).

There are bunches of flowers scattered randomly around the world.  Not too dense. Haven’t decided how dense is the right amount. 

Bees always know where their hive is. Bees can fly at a velocity of Xm/s (whatever is realistic for a bee). 

A bee can detect a flower at a range of X meters (again whatever is appropriate). 

Bee behavior has two modes. 

The first is simple foraging. Bees might chose to exit the hive (with some probability) and fly in a random walk. They choose a direction and fly in that direction for one game step.  If they detect a flower they head for that flow and pick up pollen then fly back home. 

Once home they perform a waggle dance. A dance communicates a direction and distance to 1-N other bees in the hive. 

A bee with knowledge from seeing a dance engages in a second mode of behavior. They will fly toward the flower, pick up pollen, return and dance. A bee has some probability to forget the dance knowledge and return to foraging. 

Render bees as small dots. Color code according to mode of behavior. 

Bees leave behind a visible trail that decays to the background color over time. This allows us to observe patterns of behavior. 

There should be sliders that control the parameters.  There should be a speed sliader that controls how fast the simualtion runs.  Touching a slider (except the speed slider) resets the simulation.

# Addressing comments

Things that will need decisions before coding:

> Realistic parameters: bee speed ~7 m/s, detection range ~10m, hive population 10,000–50,000 (but visually you'd probably want 50–500). Worth picking "toy" values that look good rather than realistic ones.

Agreed that 50-500 bees is right.

> Flower fields: "bunches" implies clusters, not uniform random. How many bunches? How wide? Do flowers get depleted when visited?

Yes, clusters is what I had in mind.  I'm not sure how many bunches, maybe configurable via a slider.  Default 20.

Regarding depletion, I don't think so.  If we do depletion we need a mechanism via which new flowers spawn.  Sounds complicated.  Let's start simple.

> Waggle dance precision: does the communicated direction/distance have noise (more realistic) or is it exact? Noise would make the sim more interesting.

Agreed that noise is more interesting.  You choose the noise parameters.

> Trail decay: is this per-pixel color decay each step, or per-bee trail segment with a lifetime? Per-pixel decay is simpler and looks great.

Per pixel is what I imagined.

> "Fly toward the flower" for recruited bees: do they know the exact cell, or just the approximate direction+distance from the dance? This matters for whether they find the flower reliably.

Direction and distance with noise.  

> What happens if a recruited bee doesn't find the flower? (e.g., it overflies it) — does it switch back to random foraging?

Yes, switch back to foraging.

> Coordinate system: continuous 2D float positions rather than a grid, so this sim is architecturally quite different from termites.

Agreed. 


# Second round of comments


> Flower cluster shape — Gaussian blob around a random center seems natural. Cluster radius configurable or fixed?

Sure. Gaussian blobs.

> "Forget" probability for recruited bees — you mentioned "some probability to forget dance knowledge and return to foraging." Is this per-step, or after arriving at the target location and not finding anything?

I was thinking per step.  Let's try that first.


> Trail decay rate — related to the speed slider? A fast sim would need faster decay or trails would be perpetually saturated. I'd probably tie decay rate to sim speed or make it a separate slider.

Agreed that tied to sim speed seems reasonable.

> Bees inside the hive — are they rendered? They could sit invisible until they exit, or be shown as a cluster at the center.

I think they are invisible.

> Dance audience size — "1 to N other bees" — is N a fixed cap, or does it scale with hive population?

I think fixed.  That seems more realistic.

