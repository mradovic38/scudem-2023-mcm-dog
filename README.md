# SCUDEM 2023 MCM: Dog Cannot Catch


This project contains a small physics simulation of a dog trying to catch a thrown object (ball,
sausage, pizza, taco, steak, fry) as a part of the solution for SCUDEM 20203 MCM Problem C: Dog Cannot Catch. 
A throw is generated with some aiming error, the object flies under gravity and air drag, and the dog reacts, runs,
jumps, and snaps its jaw shut to intercept it.

Two dogs are modelled with the same code but different parameters:

* **Optimal**: an idealized dog with fast reactions and no mistiming (~92% catch rate).
* **Fitz**: real dog from the problem: slower, later reactions, and prone to jump/jaw mistiming (~23% catch rate).

This document explains every mechanic mathematically. Symbols follow the code:
positions are in metres, times in seconds, angles in radians (unless stated as
degrees), $g = 9.81\ \mathrm{m/s^2}$ and air density $\rho = 1.225\ \mathrm{kg/m^3}$.


Full task details are available here under "Problem C" section: https://qubeshub.org/community/groups/simiode/File:/uploads/docs/SCUDEMVIII2023/SCUDEM_VIII_2023_All_Three_Problems.pdf

---

## 1. Drag coefficient simulation

Each throwable object is described by its mass $m$, frontal area $A$, and a
dimensionless shape drag coefficient $c_d$. Instead of hard-coding a drag
constant, the simulation derives an effective per-object drag term from these
physical properties.

Standard quadratic aerodynamic drag produces a force

$$
F_d = \tfrac{1}{2}\, c_d\, \rho\, A\, v^2 .
$$

Dividing by the mass to get an acceleration, $a_d = F_d/m$, the constant factor
in front of $v^2$ is what the code calls the **drag term** $k$:

$$
k = \frac{c_d\, \rho\, A}{2\, m}\qquad\Bigl[\mathrm{m^{-1}}\Bigr].
$$

This single number $k$ summarizes "how strongly this object is slowed by the
air per unit speed squared". Light, draggy objects (a fry, $k \approx 0.17$)
decelerate far more than dense, compact ones (a ball, $k \approx 0.018$).

*Code:* `objects.py → simulated_drag()`, producing `DRAG_COEFFS`.

---

## 2. Ball trajectory (projectile motion with drag)

The thrown object is a point mass under gravity plus quadratic drag opposing its
velocity. With velocity $\mathbf{v} = (v_x, v_y)$ and speed
$v = \lVert\mathbf v\rVert = \sqrt{v_x^2 + v_y^2}$, the accelerations are

$$
a_x = -k\, v_x\, v,
\qquad
a_y = -g - k\, v_y\, v .
$$

The $-k v_i v$ form makes drag act **along** the velocity vector with magnitude
$k v^2$, because $\frac{v_i}{v}\,(k v^2) = k v_i v$.

There is no closed form, so the trajectory is integrated with **semi-implicit
(symplectic) Euler** at a fixed step $\Delta t = 0.01\,\mathrm{s}$:

$$
\begin{aligned}
v_x &\leftarrow v_x + a_x\,\Delta t, &
v_y &\leftarrow v_y + a_y\,\Delta t, \\
x   &\leftarrow x + v_x\,\Delta t, &
y   &\leftarrow y + v_y\,\Delta t .
\end{aligned}
$$

Velocity is updated first, then position uses the new velocity. Integration
starts at launch height $h_0$ and stops when $y < 0$ (ground impact), yielding
sampled arrays $t_i, x_i, y_i$. The position at an arbitrary time is obtained by
linear interpolation between samples:

$$
x(t) = \operatorname{lerp}(t;\, t_i, x_i),
\qquad
y(t) = \operatorname{lerp}(t;\, t_i, y_i).
$$

*Code:* `physics.py → generate_ball_trajectory()`, `compute_ball_position_at_time()`.

---

## 3. Aiming the throw

The dog rests at horizontal position $g_x \in [1.2, 1.8]$ m with its head at
height $\mathrm{GOAL\_Y} = 0.55$ m. The thrower *aims* at the dog but misses by a
random offset sampled **uniformly over a disc** of radius
$R = \mathrm{THROW\_ERROR\_RADIUS} = 0.3$ m. To get a uniform distribution over
the disc area (not clustered at the centre), the radius uses a square root:

$$
r = R\sqrt{u_1},\quad \theta = 2\pi u_2,\quad u_1,u_2 \sim \mathcal U(0,1),
$$

$$
x_\text{target} = g_x + r\cos\theta,
\qquad
y_\text{target} = \mathrm{GOAL\_Y} + r\sin\theta .
$$

The launch height $h_0 \sim \mathcal U(1.2, 1.4)$ m and launch angle
$\alpha \sim \mathcal U(20^\circ, 45^\circ)$ are also randomized.

### Solving for the launch speed

Given the angle $\alpha$ and the desired target point
$(x_\text{target}, y_\text{target})$, we need the launch speed $v_0$ that makes a
**drag-free** projectile pass through that point. Starting from the standard
trajectory equation

$$
y = h_0 + x\tan\alpha - \frac{g\,x^2}{2\,v_0^2\cos^2\alpha},
$$

and solving for $v_0$ at $x = x_\text{target}$, $y = y_\text{target}$:

$$
v_0 = \sqrt{\dfrac{g\,x_\text{target}^2}
{2\cos^2\alpha\,\bigl(h_0 - y_\text{target} + x_\text{target}\tan\alpha\bigr)}} .
$$

If the denominator is $\le 0$ the geometry is unreachable and the throw is
rejected. The launch velocity components are then
$v_x = v_0\cos\alpha$ and $v_y = v_0\sin\alpha$.

Note: $v_0$ is solved **without** drag (closed form), but the actual flight is
then integrated **with** drag, so the object lands a bit short of the aim point, which makes for
a deliberate, realistic imperfection.

*Code:* `simulation` cell → `_setup_throw()`.

---

## 4. Dog running kinematics

A dog does not move at constant speed; it accelerates from rest toward a top
speed. The model uses a smooth burst-acceleration law in which acceleration
tapers as speed approaches the maximum $v_{\max}$, equivalent to
$\dot v = a_0\bigl(1 - (v/v_{\max})^2\bigr)$. This integrates to a hyperbolic
tangent speed profile:

$$
v(t) = v_{\max} \tanh\!\left(\frac{a_0\, t}{v_{\max}}\right).
$$

Integrating once more gives the distance travelled from a standing start:

$$
d(t) = \frac{v_{\max}^2}{a_0}\,
\ln\!\cosh\!\left(\frac{a_0\, t}{v_{\max}}\right).
$$

Here $a_0$ is the initial burst acceleration and $v_{\max}$ the top speed (Optimal:
$a_0 = 15,\ v_{\max} = 12$; Fitz: $a_0 = 7,\ v_{\max} = 8$).

### Inverting distance → time

To plan an interception we also need the time to cover a given distance $d$,
i.e. invert $d(t)$. Since $d(t)$ is monotonically increasing, it is inverted by
**bisection** (50 iterations) on the interval
$[0,\ d/v_{\max} + v_{\max}/a_0]$ (the upper bound is the cruise time plus a slack
term covering the acceleration phase).

*Code:* `physics.py → dog_velocity()`, `dog_distance()`, `dog_time_for_distance()`.

---

## 5. Jump kinematics

To catch a ball at height $y_t$ above the ground, the dog must lift its head from
its rest height $\mathrm{GOAL\_Y}$ by

$$
\Delta h = \max(0,\ y_t - \mathrm{GOAL\_Y}).
$$

Treating the jump as vertical projectile motion, the take-off vertical velocity
needed to reach apex at $\Delta h$ (where $v_y = 0$) comes from
$v_y^2 = 2 g\,\Delta h$:

$$
v_{y,\text{jump}} = \sqrt{2 g\,\Delta h},
\qquad
t_\text{apex} = \frac{v_{y,\text{jump}}}{g},
\qquad
t_\text{air} = \sqrt{\frac{2\,\Delta h}{g}} .
$$

While airborne the head follows a ballistic arc, integrated per frame:

$$
y \leftarrow y + v_y\,\Delta t - \tfrac12 g\,\Delta t^2,
\qquad
v_y \leftarrow v_y - g\,\Delta t .
$$

*Code:* `dog motion` cell → `_jump_kinematics()`, `_advance_dog()`;
`interception.py → _jump_time()`.

---

## 6. Interception planning

When the dog first reacts, it predicts the entire ball path and chooses a single
target point to attack. For each candidate time $t_c$ along the remaining flight
it reads the ball position $(b_x, b_y)$ and computes:

* **time available** until the ball is there: $\;t_\text{avail} = t_c - t_\text{now}$
* **horizontal distance** to cover: $\;d = \lvert g_x - b_x\rvert$
* **total time the dog needs**: run time + jump time,

$$
t_\text{need} = \underbrace{d^{-1}\!\!\;(d)}_{\text{run, from §4}} \; + \;
\underbrace{\sqrt{2\,\Delta h / g}}_{\text{jump, from §5}} .
$$

The planner prefers a point that is **in front of the dog** ($b_x < g_x$) and
**above head height** ($b_y > \mathrm{GOAL\_Y}$). Among those it picks by:

1. **Reachable** ($t_\text{need} \le t_\text{avail}$): minimize the timing error
   $\lvert t_\text{avail} - t_\text{need}\rvert$ (i.e. the catch that needs the
   least waiting/rushing).
2. If none are reachable, the **least-unreachable** one: minimize the deficit
   $t_\text{need} - t_\text{avail}$.
3. Otherwise a pure-running **fallback**: any point the dog can reach by distance
   alone ($d(t_\text{avail}) \ge d$), choosing the highest such ball point.

*Code:* `interception.py → compute_interception()`.

### Departure timing

Once the target time $t^*$ and point are known, the dog should leave so it
arrives exactly on time, not immediately. With run time $t_\text{run}$ and jump
time $t_\text{jump}$ to the target, the depart time is

$$
t_\text{depart} = \max\bigl(t_\text{react},\ t^* - t_\text{run} - t_\text{jump}\bigr).
$$

---

## 7. Dog motion state machine

Each frame the dog is in one of three states, handled in `_advance_dog()`:

1. **Airborne** ($y > 0.01$): follow the ballistic arc (§5), clamping $x$ at the
   target and landing when $y \le 0$.
2. **Running** ($\lvert\Delta x\rvert > 0.02$): advance horizontally at the
   current run speed $v(t_\text{run})$ (§4), signed toward the target. Jump when
   the **time remaining** drops to the apex time (plus mistiming, §9):

$$
t^* - t_\text{now} \;\le\; t_\text{apex} + \epsilon_\text{jump}.
$$

3. **In position**: wait until the same jump condition triggers, then launch.

Positions are stored as $(x,\ \text{height above rest})$ per frame; the head is
drawn at $y_\text{head} = y + \mathrm{GOAL\_Y}$.

*Code:* `dog motion` cell → `_advance_dog()`, `simulate_dog_motion()`.

---

## 8. Jaw aiming, rotation and closing

### Aim direction

The jaw should meet the ball head-on. Using the ball's velocity at the intercept
time (estimated by finite difference, $\mathbf v_b \approx [\mathbf b(t^*+\delta) - \mathbf b(t^*)]/\delta$),
the desired jaw direction points *back along* the incoming ball:

$$
\phi_\text{aim} = \operatorname{atan2}(-v_{b,y},\,-v_{b,x})
                 + \phi_\text{offset} + \epsilon_\text{jaw},
$$

where $\phi_\text{offset}$ is a fixed bite offset and $\epsilon_\text{jaw}$ a
random aiming error (§9). The target is stored as the unit vector
$(\cos\phi_\text{aim}, \sin\phi_\text{aim})$.

*Code:* `dog motion` cell → `compute_jaw_target()`.

### Rotation toward the aim

The jaw starts pointing left ($\phi_0 = \pi$) and rotates toward $\phi_\text{aim}$
at a finite angular rate $\omega$. With elapsed time $\tau$ since the dog saw the
ball, and the shortest signed angular difference

$$
\Delta\phi = \bigl((\phi_\text{aim} - \phi_0 + \pi) \bmod 2\pi\bigr) - \pi,
$$

the current jaw angle is the wrapped, rate-limited rotation

$$
\phi(\tau) = \phi_0 + \operatorname{sign}(\Delta\phi)\,
\min\bigl(\lvert\Delta\phi\rvert,\ \omega\,\tau\bigr).
$$

*Code:* `jaw helpers` cell → `rotated_jaw_angle()`.

### Opening and snapping shut

The mouth opens gradually as the dog approaches the intercept, reaching its full
half-angle $\theta_\text{open}$ at the catch, then snaps shut over a short
duration $T_c$. Let $t_\text{trig}$ be the closing trigger time. The opening
half-angle is

$$
\theta(t) =
\begin{cases}
\theta_\text{open}\,\dfrac{t - t_\text{react}}{t^* - t_\text{react}}, & t < t_\text{trig}\quad(\text{opening}),\\[2ex]
\theta_\text{open}\left(1 - \dfrac{t - t_\text{trig}}{T_c}\right), & t_\text{trig} \le t < t_\text{trig} + T_c\quad(\text{closing}),\\[2ex]
0, & \text{otherwise (shut).}
\end{cases}
$$

*Code:* `jaw helpers` cell → `jaw_open_closing()`; `visualization.py → _jaw_open_amount()`.

---

## 9. Per-dog error and mistiming

What separates Optimal from Fitz is randomized error, sampled uniformly per
attempt from per-dog ranges:

| Symbol | Meaning | Optimal | Fitz |
| --- | --- | --- | --- |
| reaction delay | $t_\text{react} \sim \mathcal U(\cdot)$ ms | $[150, 300]$ | $[250, 350]$ |
| $\epsilon_\text{jump}$ | jump mistiming (s) | $0$ | $[-0.25, 0.25]$ |
| $\epsilon_\text{jaw}$ | jaw aim error (rad) | $0$ | $[-0.4, 0.4]$ |
| jaw-close mistime | trigger offset (s) | $0$ | $[-0.15, 0]$ |

A positive $\epsilon_\text{jump}$ makes the dog jump late; a non-zero
$\epsilon_\text{jaw}$ rotates the bite off the true incoming direction; a
negative close-mistime snaps the jaw early. These feed directly into the
formulas of §7 and §8.

The dog's **perception** is also delayed: it only "sees" the ball at its position
$t_\text{react}$ seconds in the past, which is why the blue perception marker
lags the red ball in the animation.

*Code:* `DogProfile` (`dog_profile.py`); sampled in `_setup_throw()`.

---

## 10. Catch detection

After simulating motion, success is decided geometrically. Around the intercept
time the code samples 20 instants $t \in [t^* - 0.05,\ t^* + 0.05]$. At each it
computes the vector from the dog's head to the ball,
$\mathbf r = \mathbf b - \mathbf{head}$, and declares a catch if **both**:

1. The ball is within reach (jaw length / catch radius $L$):

$$
\lVert \mathbf r \rVert \le L .
$$

2. The ball lies inside the open jaw cone: the angle between $\mathbf r$ and the
   current jaw direction $\phi(t)$ is within the current opening (plus a small
   tolerance):

$$
\bigl\lvert\operatorname{wrap}(\operatorname{atan2}(r_y, r_x) - \phi(t))\bigr\rvert
\;\le\; \theta(t) + 0.01,
$$

where $\operatorname{wrap}$ maps an angle to $(-\pi, \pi]$ via
$((\cdot + \pi) \bmod 2\pi) - \pi$, and $\theta(t)$ is the closing-jaw half-angle
from §8. If any sampled instant satisfies both, the attempt is a success.

*Code:* `jaw helpers` cell → `check_catch_success()`.

---

## 11. Timeline & animation

The simulation runs on a fixed frame grid. The total duration is the flight time
plus the reaction delay plus a 0.3 s tail, sampled at $\mathrm{FPS} = 30$:

$$
T = t_\text{flight} + t_\text{react} + 0.3,
\qquad
N = \max(2,\ \lfloor T \cdot \mathrm{FPS}\rfloor),
\qquad
t = \operatorname{linspace}(0, T, N).
$$

The animation shows the **true** ball (red), the dog's time-delayed
**perception** (blue, shifted by $t_\text{react}$), the dog (green), its heading
arrow, and the two jaw lines. Each frame is $1000/\mathrm{FPS} \approx 33.3$ ms.

*Code:* `simulation` cell → `_build_timeline()`, `simulate()`;
`visualization.py → plot()`.

---

## Module map

| File | Contents |
| --- | --- |
| `constants.py` | World & physics constants ($g$, $\rho$, throw ranges, goal, FPS) |
| `objects.py` | Throwable objects + drag-term simulation |
| `physics.py` | Ball trajectory & dog kinematics |
| `interception.py` | Interception planning |
| `dog_profile.py` | `DogProfile` dataclass; defaults = Optimal dog |
| `visualization.py` | Animation |
| `main.ipynb` / `main.py` | Dog motion, jaw/catch logic, profiles, high-level driver |