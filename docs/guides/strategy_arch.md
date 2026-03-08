# Context
The American Solar Car challenge is a long distance across the US for solar cars! The goal of the strategy team is to find a critical/optimal speed to drive at. We compete in the SOV class:

> Single-Occupant vehicle teams will be ranked based on Official Distance driven (higher distance is best). Should teams tie on Official Distance, Official Elapsed Time will be used as a tie-breaker to determine ranking (shorter elapsed time is best).

Each day, there is a base route that our solar car must complete. At select checkpoints, there is the option to repeatedly drive around in a loop to increase event distance, so if we finish our base route early, this is a great avenue to gain additional distance. Clearly, therefore, the main goal of our solar car’s strategy team will be to maximize distance and minimize time for ASC 2026.

# Defining the Problem Statement

Our goal is to choose a speed profile that maximizes expected official distance over a time period $[0, t]$, where $t$ is the total driving time allowed for that day. Our constraint is that the battery state of charge (SOC) must remain above 20% at the end of the day.

# Overview of Solar Car Strategy

## Simulation

A good solar car strategy requires a good simulation model. Our current simulation models power lost through the drivetrain and power gained from the solar array.

### Drivetrain

For the drivetrain, we calculate three main power components. Recall that power is force times velocity:

$$
P = Fv
$$

Thus, we model rolling resistance, aerodynamic drag, and road grade as:

$$
\begin{aligned}
P_{rr} &= C_{rr} m g \, v \\
P_{drag} &= \frac{1}{2} \rho C_d A v^3 \\
P_{grade} &= m g \sin(\theta)\, v
\end{aligned}
$$

where:
- $C_{rr}$ is the rolling resistance coefficient,
- $m$ is the mass of the vehicle,
- $g$ is gravitational acceleration,
- $\rho$ is air density,
- $C_d$ is the drag coefficient,
- $A$ is frontal area,
- $\theta$ is the road grade angle.

### Solar Power

For solar power, we use:

$$
\begin{aligned}
P_{solar} &= A_{solar}\,\eta_{panel}\,G
\end{aligned}
$$

where $\eta_{panel}$ is panel efficiency and $G$ is the estimated irradiance.

### Net Battery Power

To account for drivetrain efficiency, we model the battery-side drivetrain power as:

$$
\begin{aligned}
P_{rr,\text{drive}} &= \frac{P_{rr}}{\eta_{drive}} \\
P_{drag,\text{drive}} &= \frac{P_{drag}}{\eta_{drive}} \\
P_{grade,\text{drive}} &= \frac{\max(P_{grade}, 0)}{\eta_{drive}}
\end{aligned}
$$

Currently, the simulation does not yet account for regenerative braking, which is why the term $\max(P_{grade}, 0)$ is used. In other words, downhill gravitational power is not currently recovered into the battery.

The net battery power draw is then

$$
P_{net} = P_{rr,\text{drive}} + P_{drag,\text{drive}} + P_{grade,\text{drive}} - P_{solar}
$$

Here, positive terms represent battery power consumption, while solar power is subtracted since it offsets battery usage.

Since power is energy per unit time, over one timestep we have:

$$
E_{net,k} = P_{net,k}\,\Delta t
$$

## Optimization

The goal of the optimizer is to choose a speed profile that maximizes total distance traveled.

Let the speed profile be

$$
v = [v_0, v_1, \dots, v_{N-1}] \in \mathbb{R}^N
$$

where $N$ is the number of time divisions in the optimization horizon.

For example, if we split a 9-hour driving period into 60-minute intervals, then $N = 9$.

To compute how the car’s position changes over time, we start from the 1st order ODE:

$$
\frac{dd}{dt} = v(t)
$$

Using forward Euler integration, distance evolves according to

$$
d_{k+1} = d_k + v_k \Delta t
$$

Since our simulation is evaluated at discrete time steps rather than continuous, we approximate this differential equation using the [Forward Euler method](https://math.libretexts.org/Bookshelves/Differential_Equations/Numerically_Solving_Ordinary_Differential_Equations_(Brorson)/01%3A_Chapters/1.02%3A_Forward_Euler_method). Applying Forward Euler with timestep $\delta t$ gives

$$
d_{k+1} = d_k + v_k \Delta t
$$

Extrapolating:

$$
d_N = d_0 + \sum_{k=0}^{N-1} v_k \Delta t
$$

Thus, maximizing final distance is equivalent to maximizing

$$
J(v) = d_0 + \sum_{k=0}^{N-1} v_k \Delta t
$$

Since $d_0$ is constant, this is also equivalent to maximizing

$$
\sum_{k=0}^{N-1} v_k \Delta t
$$

In code, however, you may notice us minimizing $-J(v)$, but they are essentially doing the same thing. 
### Battery Energy Constraint

Recall from the problem statement that SOC must remain above 20% at the end of the day.

At each timestep, battery energy evolves as

$$
E_{bat,k+1} = E_{bat,k} - E_{net,k}
$$

or equivalently,

$$
E_{bat,k+1} = E_{bat,k} - P_{net,k}\,\Delta t
$$

The state of charge is defined as the remaining battery energy divided by the maximum battery energy:

$$
SOC_k = \frac{E_{bat,k}}{E_{bat,\max}}
$$

Therefore, the end-of-day SOC constraint is

$$
SOC_N \geq 0.2
$$

or equivalently,

$$
E_{bat,N} \geq 0.2\,E_{bat,\max}
$$

## Formal Optimization Problem

More formally, the optimization problem can be written as

$$
\begin{aligned}
\min_{v \in \mathbb{R}^N} \quad & -J(v) \\
\text{with constraints} \quad
& v_{\min} \leq v_k \leq v_{\max}, \\
& E_{bat,N} \geq 0.2\,E_{bat,\max}
\end{aligned}
$$

### Optimization Methods
Now there are several ways of optimizing for our problem, we use a gradient based one called [SLSQP](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html). In the future we may try other optimization algorithms. 


# Note on Benchmarking
In the future we will be benchmarking our optimization algorithms. To do this, we will evaluate them on smaller problem instances and compare their results to an [exhaustic search](https://en.wikipedia.org/wiki/Brute-force_search) (Tries every single possible vector). This allows us to determine whether the optimizer converges to the correct solution and how many iterations it requires to reach it.

To bench mark our simulation models, the plan is to get data from the car about speeds driven at versus SOC lost, and tweaking our model until we get similar results to ones observed.

# Implementing it in Code:
The diagram below serves as a good model to what we do and plan on doing:
![](../architecture.svg)