# -*- coding: utf-8 -*-
"""
no-fan temperature box, real-time digital twin (Euler, two-capacity model)

The "simplified" version simplifies away the FAN, but keeps the heater's
own thermal inertia. The thermal circuit therefore has two nodes:

       eta*P            (T_h-T_a)/R_ha          (T_a-T_e)/R_ae
   ---------> [Th, Ch] -----------------> [Ta, Ca] -----------------> Tenv

   C_h dT_h/dt = eta*P - (T_h - T_a)/R_ha
   C_a dT_a/dt = (T_h - T_a)/R_ha - (T_a - T_e)/R_ae

Naming convention (formula <-> code):
   T_h  <-> temp_h     heater-element temperature
   T_a  <-> temp_a     air (controlled) temperature
   P    <-> power      heater electrical power
   T_e  <-> t_env      ambient temperature
   C_h  <-> c_h        heater heat capacity
   C_a  <-> c_a        air-side heat capacity
   eta  <-> eta        heater electric->thermal efficiency
   R_ha <-> r_ha       heater -> air thermal resistance
   R_ae <-> r_ae       air    -> ambient thermal resistance
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- 1. physical parameters ----
c_h   = 200.0     # heater heat capacity      [J/K]
c_a   = 1500.0    # air + inner-shell capacity [J/K]
eta   = 0.95      # heater efficiency          [-]
r_ha  = 0.10      # heater -> air resistance   [K/W]
r_ae  = 0.40      # air    -> env resistance   [K/W]
t_env = 25.0      # ambient temperature        [C]

# ---- 2. input signal P(t) ----
def get_power(t):
    """Heater power profile: off when t<30s, then 200 W."""
    return 200.0 if t >= 30.0 else 0.0

# ---- 3. one-step advance (two-capacity model, real-time digital-twin core) ----
def step_euler(temp_h, temp_a, power, dt):
    """Advance (T_h, T_a) by one sampling period dt with explicit Euler."""
    q_ha = (temp_h - temp_a) / r_ha     # heater -> air heat flow
    q_ae = (temp_a - t_env)  / r_ae     # air    -> env heat flow
    d_temp_h = (eta * power - q_ha) / c_h
    d_temp_a = (q_ha        - q_ae) / c_a
    return temp_h + dt * d_temp_h, temp_a + dt * d_temp_a

# ---- 4. real-time main loop ----
temp_h = t_env
temp_a = t_env
dt     = 1.0
t_end  = 3500.0   # 5*tau_a, 让空气也走到稳态

ts      = [0.0]
temps_h = [temp_h]
temps_a = [temp_a]
powers  = [get_power(0.0)]

t = 0.0
while t < t_end:
    power = get_power(t)
    temp_h, temp_a = step_euler(temp_h, temp_a, power, dt)
    t += dt
    ts.append(t)
    temps_h.append(temp_h)
    temps_a.append(temp_a)
    powers.append(power)
    # In a true real-time system we would wait for the next sampling tick:
    #   time.sleep(dt) or be triggered by a hardware interrupt.

# ---- 5. plot ----
out = os.path.join(os.path.dirname(__file__), "..", "figures")
os.makedirs(out, exist_ok=True)

fig, ax1 = plt.subplots(figsize=(8, 4.4))
ax1.plot(ts, temps_h, "r-", linewidth=1.6, label="T_h heater (Euler dt=1s)")
ax1.plot(ts, temps_a, "b-", linewidth=1.6, label="T_a air    (Euler dt=1s)")
ax1.set_xlabel("Time / s")
ax1.set_ylabel("Temperature / C")
ax1.grid(True, alpha=0.4)
ax1.legend(loc="upper left", fontsize=9)

ax2 = ax1.twinx()
ax2.plot(ts, powers, "k--", alpha=0.45, label="power (W)")
ax2.set_ylabel("Heater power / W")
ax2.legend(loc="lower right", fontsize=9)

ax1.set_title("No-fan, two-capacity real-time Euler simulation (dt=1s)")
fig.tight_layout()
fig.savefig(os.path.join(out, "no_fan_euler.png"), dpi=140)
plt.close(fig)
print("Saved no_fan_euler.png  | T_a={:.2f}C, T_h={:.2f}C".format(temps_a[-1], temps_h[-1]))
