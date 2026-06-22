# FormulaMind — AI F1 Strategy & Telemetry Platform

FormulaMind is a full-stack, data-driven F1 Race Engineering console. It connects directly to live timing and telemetry databases to optimize pit stint strategies, analyze undercut threats, compare driver speed profiles, and simulate multi-agent race scenarios under dynamic track conditions (like Safety Cars and rain weather).

---
## Live Application Links
* **Direct Application**: [https://awantigiradkar-formulamind.hf.space](https://awantigiradkar-formulamind.hf.space)

### Dashboard Console View
<img width="946" height="412" alt="Screenshot 2026-06-22 230656" src="https://github.com/user-attachments/assets/5602bbf8-75d9-46a3-809b-d86c7fbd24dd" />

---

## What Everything Is & How It Works
### 1. Timing API Settings (Sidebar Control Panel)
* **What it is**: The data gateway where you select the F1 Season (2021–2026), Grand Prix, and Session (Qualifying or Race), and connect the API.
* **How it works**: 
  * Clicking **Connect Timing API** sends a POST request to `/api/connect`.
  * The backend initializes the **FastF1** engine and attempts to fetch official telemetry.
  * If a session has not occurred yet (e.g., in the future), the server checks the official calendar schedule and throws an HTTP 400 error: `"This race has not happened yet."`
  * If data is missing or corrupted, a **self-healing fallback** loads the cached **Silverstone 2023** database instead.
  * Once loaded, the server automatically **trains a Random Forest Regressor** in the background on the session's clean dry-weather laps to model tyre wear decay.
---
### 2. Telemetry comparison Tab
* **What it is**: A comparison suite that overlays sensor data from two drivers to analyze apex speed, acceleration profiles, gear shifting, and track dominance.
* **How it works**:
  * **Distance Alignment**: Since two drivers take different racing lines and log data at different times, the engine maps their telemetry points onto a uniform **1,000-point distance grid**.
  * **Gap Delta Line**: Calculates a running gap delta ($t_A - t_B$) along the lap using cumulative integration:
    $$\text{Time} = \int \frac{1}{\text{Speed}} \, dx$$
  * **DRS Active Zones**: Scans the telemetry stream for DRS values $\ge 10$. It highlights active zones as translucent cyan rectangles on the Speed chart.
  * **2D Dominance Map**: Interpolates 2D coordinates ($X, Y$) from telemetry. At each point, it evaluates who had the higher speed and maps the faster driver's team color onto that coordinate.
  * **Style Signature Radar**: Evaluates five metrics on a $50\text{–}100$ scale:
    * *Straight-Line Speed*: Top speeds relative to a $260\text{–}340\text{ km/h}$ range.
    * *Braking Aggression*: Average deceleration magnitude in active braking zones.
    * *Throttle Application*: Throttle percentage distribution.
    * *Corner Apex Speed*: Average speed during the slowest 15% of the lap.
    * *Gear Shift Efficiency*: Shift count comparison.
---
### 3. AI Strategy & Stint Optimizer Tab
* **What it is**: An AI stint strategist that calculates tyre degradation and ranks optimal race strategies.
* **How it works**:
  * **Tyre Decay Simulation**: Utilizes the Random Forest model to project tyre wear:
    $$\text{Lap Time} = f(\text{TyreLife}, \text{LapNumber}, \text{Compound})$$
  * **Fuel Burn Correction**: Automatically adds $+0.065\text{s}$ per lap to model the weight decay of the car as fuel is consumed.
  * **Strategy Optimization (1-Stop & 2-Stop)**: Runs a grid search over realistic pit window boundaries (e.g., Laps 10–32 for Mediums) to find the pit lap that minimizes total race duration:
    $$\text{Total Duration} = \sum (\text{Stint Laps}) + \text{Pit Stop Loss}$$
  * **Traffic Window Planner**: Establishes a $2.0\text{s}$ margin threshold around competitors' projected track positions. If a pit stop re-entry places you within this margin, it flags the lap as a `Traffic Blocker` and names the competitor (e.g. Albon or Hamilton); otherwise, it is flagged as `Clean Air`.
---
### 4. Live Pit Lane Undercut Analyzer Tab
* **What it is**: A tool to evaluate if a trailing driver (chaser) can pass the leader on track by pitting early for fresh tyres.
* **How it works**:
  * Calculates the chaser's out-lap on fresh tyres (Age = 1) versus the leader staying out for one more lap on worn tyres (Age + 1):
    $$\text{Undercut Gain} = \text{Leader Worn Out-lap Time} - \text{Chaser Fresh Out-lap Time}$$
  * Subtracts the gain from the current gap ($G_{\text{current}} - \Delta t$).
  * If the resulting gap is **negative**, the undercut is successful and a `CRITICAL` threat alert is triggered.
---
### 5. Multi-Driver Strategy Race Simulator Tab
* **What it is**: A simulator that runs a discrete-event race simulation lap-by-lap for selected drivers under dynamic weather and safety car parameters.
* **How it works**:
  * **Rain Multipliers**: Applies a severe penalty ($+15.0\text{s}$ to $+25.0\text{s}$) if slick tyres are run on a wet track. Conversely, running wet tyres on a dry track adds a $+12.0\text{s}$ penalty to model tread block overheating.
  * **Safety Car periods**: Forces a slow delta speed ($120.0\text{s}$ delta lap) for all drivers and reduces pit stop lane overhead from $20.0\text{s}$ to **$12.0\text{s}$** (modeling cheap pit stops under SC).
  * **Lap-by-Lap Position Tracker**: Re-sorts driver cumulative times at the end of each lap to update the standings board and render the running positions on the Plotly chart.
---
### 6. Pit Wall AI Strategy Assistant Tab
* **What it is**: A chatbot built directly into the pit wall console that responds to race strategy and weather queries.
* **How it works**:
  * Uses a keyword parser to intercept topics (e.g., `strategy`, `undercut`, `weather`).
  * Triggers live backend calculations (e.g. fetches the current track temp, runs stint optimization, or checks chaser out-lap deltas) and formats the output in a professional F1 Pit Wall Radio dispatch.
---

## Technology Stack
* **Backend**: FastAPI (Python), FastF1 (Timing API), Scikit-Learn (Random Forest Regressor), Pandas, NumPy.
* **Frontend**: HTML5, CSS3 (Glassmorphism layout, glowing animations), JavaScript (ES6).
* **Visualizations**: Plotly.js (interactive, responsive layouts).
* **Deployment**: Docker, Git LFS (binary assets), Hugging Face Spaces.

## Local Setup & Installation

### Prerequisites
Make sure you have Python 3.10+ installed on your system.

### 1. Clone and Navigate
```bash
git clone https://github.com/awantigiradkar/FormulaMind.git
cd FormulaMind
```
### 2.Configure Virtual Environment
```powershell
# Create environment
python -m venv env
# Activate environment (Windows PowerShell)
.\env\Scripts\activate
# Activate environment (Mac/Linux)
source env/bin/activate
```

### 3.Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Dev Server
```bash
python server.py
```
Open http://127.0.0.1:8000 in your web browser to access the console dashboard locally!

## Cloud Deployment (Hugging Face Spaces)
This project is configured to run on Hugging Face Spaces using the Docker SDK.

Space Settings: Create a new Hugging Face Space, select Docker as the SDK, and choose Blank template.
Git LFS: Track binary images using Git LFS before pushing:
```bash
git lfs install
git lfs track "*.png"
git lfs migrate import --include="*.png" --everything
Push to Space:
```
```bash
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
git push hf main --force
```
