## This is the custom constellation project by Ithea and Lauren! This is the code file used in the Streamlit app.
## We were unsure how to do markdown cells like in Juypter Lab, but for our descriptions we will be using the hashtags to talk about our code. 

import matplotlib
import sys
if __name__ == "__main__":
    matplotlib.use('TkAgg') # Force window popup for animate_sky()
else:
    matplotlib.use('Agg') #For Streamlit — avoids 'freeze when trying to open a display

## The first few lines are just for the animation to work properly. So ideally, we should be able to run this code
## by itself without the Streamlit part to test the animation. Streamlit does not like it when you try to run the animation.
## So in short, if the code is ran locally, it should use TkAgg to open a window to display the animation.
## And if imported by Streamlit, it should use Agg to avoid the freeze. This is just a check for us to make sure streamlit is working fine.

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import json
import os
import random
import math


# --- 1. THE CLASSES --- #

class Star:
    def __init__(self, star_id, azimuth, altitude, magnitude):
        self.id = star_id
        self.azimuth = azimuth # Angle in radians (0 to 2pi)
        self.altitude = altitude # Distance from center (0 to 1)
        self.magnitude = magnitude
        self.update_xy()

    def update_xy(self):
        """Recalculates X/Y coordinates based on current Azimuth/Altitude."""
        self.x = self.altitude * np.cos(self.azimuth)
        self.y = self.altitude * np.sin(self.azimuth)
    
    def distance_to(self, other_star):
        return math.sqrt((self.x - other_star.x)**2 + (self.y - other_star.y)**2)

    def rotate(self, hours):
        """Rotates the star. Earth rotates 15 degrees (pi/12 radians) per hour."""
        rotation_speed = np.pi / 12 
        self.azimuth += (hours * rotation_speed)
        self.azimuth %= (2 * np.pi)
        self.update_xy()

    def to_dict(self):
        return {
            "id": self.id, "azimuth": self.azimuth, 
            "altitude": self.altitude, "magnitude": self.magnitude
        }

## This builds the Class for stars. Each star stores its position in the sky (azimuth and altitude) - as polar coordinates - and its magnitude.
## This will help us in creating a sky like map that we typically see in a lot of astronomy rather than just a flat map.
## The update_xy converts the polar coordinates to Cartesian coordinates (x, y) for easier calculation of distances between stars.
## It is easier to find these distances using trig in Cartesian rather than polar, I don't like working with polar unless necessary.
## The rotate function is used to rotate the star around the center of the sky. This was used in the animation to make it look like the sky is rotating.
## So even though we scraped the animation idea for Streamlit, it lives in the code with no issue.
## And finally, the to_dict function is used to convert the star object to a dictionary for easy saving and loading of the universe.

class Constellation:
    def __init__(self, cid, stars=None, mythology="Unknown"):
        self.cid = cid
        self.stars = stars if stars else [] 
        self.edges = [] 
        self.mythology = mythology
        self.is_closed = random.choice([True, False])
    
    def add_star(self, star):
        if star not in self.stars:
            self.stars.append(star)
    
    def get_center(self):
        """Calculates center point using vector math to handle wrapping."""
        if not self.stars: return 0, 0
        
        xs = [s.altitude * np.cos(s.azimuth) for s in self.stars]
        ys = [s.altitude * np.sin(s.azimuth) for s in self.stars]
        
        mean_x = np.mean(xs)
        mean_y = np.mean(ys)
        
        center_alt = np.sqrt(mean_x**2 + mean_y**2)
        center_az = np.arctan2(mean_y, mean_x)
        
        return center_az, center_alt

    def to_dict(self):
        return {
            "id": self.cid,
            "star_ids": [s.id for s in self.stars],
            "mythology": self.mythology
        }

## This builds the Class for constellations. It represents a group of stars that are connected to each other.
## It stores the stars in the constellations, the list of edges (or rather the pairs of stars that form lines), and the mythology string.
## The random choice for is_closed is used to make some constellations closed and some open. We were having trouble making the constellations not look like rectangles.
## So for a closed constellation, it would be similar to a polygon. And then a open one would be like a line or a combo like the Dippers we know. 
## The get center function figures out where the visual center of the constellation is. This is used to place the name of the constellation in the center of the constellation.
## And similarly, the to_dict function is used to convert the constellation object to a dictionary for easy saving and loading of the universe.


# --- 2. THE GENERATORS --- #

def generate_stars(num_stars=150, seed=None):
    if seed: np.random.seed(seed)
    stars = []
    
    azimuths = np.random.uniform(0, 2*np.pi, num_stars)
    altitudes = np.sqrt(np.random.uniform(0, 1, num_stars)) 
    magnitudes = np.random.exponential(scale=2.0, size=num_stars) + 1
    magnitudes = np.clip(magnitudes, 1, 6)
    
    for i in range(num_stars):
        stars.append(Star(i, azimuths[i], altitudes[i], magnitudes[i]))
    return stars

## This function generates the stars. It creates a list of stars with random azimuths, altitudes, and magnitudes.
## The azimuths are spread out evenly through the sky in a full circle. The altitudes are spread out from the center of the sky to the edge.
## The difference between the altitudes and the  azimuths is the square function that is necessary to stop the stars from being too close to the center of the sky.
## The magnitudes use an exponential distribution to give more weight to the brighter stars on a range between 1 and 6. 

def get_bright_field(star_list, threshold=5.5):
    """Requirement: Filters stars using a list comprehension."""
    return [s for s in star_list if s.magnitude <= threshold]

## This function filters the stars to only include the brightest ones. This is used to make the background of the sky not too bright.

def create_constellations(star_list, max_distance=0.35, min_spacing=0.15):
    """Finds branching networks of stars, occasionally closing them into loops."""
    constellations = []
    used_ids = set()
    c_count = 1
    sorted_stars = sorted(star_list, key=lambda s: s.magnitude)
    
    def is_trespassing(target_star):
        for const in constellations:
            for existing_star in const.stars:
                if target_star.distance_to(existing_star) < min_spacing:
                    return True
        return False

        ## This function checks if a star is too close to another star. If it is, it returns True. We had issues of constellations crossing into each other's spaces and being ugly and bad...
        ## This just enforces a minimum spacing between stars to prevent this.
    
    for anchor in sorted_stars:
        if anchor.id in used_ids or anchor.magnitude > 4.0: continue
        if is_trespassing(anchor): continue
        
        new_const = Constellation(c_count)
        new_const.add_star(anchor)
        temp_used = {anchor.id}
        
        for _ in range(12):
            best_candidate = None
            best_parent = None
            closest_dist = max_distance
            
            for candidate in star_list:
                if candidate.id in used_ids or candidate.id in temp_used: continue
                if is_trespassing(candidate): continue
                if candidate.magnitude > 4.5: continue
                
                for current_star in new_const.stars:
                    d = current_star.distance_to(candidate)
                    if d < closest_dist:
                        closest_dist = d
                        best_candidate = candidate
                        best_parent = current_star
                
                if best_candidate:
                    new_const.add_star(best_candidate)
                    new_const.edges.append((best_parent, best_candidate)) 
                    temp_used.add(best_candidate.id)
                else:
                    break 
        
        if new_const.is_closed and len(new_const.stars) >= 3:
            new_const.edges.append((new_const.stars[-1], new_const.stars[0]))
        
        if len(new_const.stars) >= 4:
            constellations.append(new_const)
            used_ids.update(temp_used) 
        c_count += 1
    
    return constellations

## And finally, we create the constellations. We start with the brightest stars and work our way down to the faintest ones.
## Using the brighest stars as anchors for these constellations make it a little easier to see the constellations come together.
## This series of functions will create any number of constellations that are connected to each other. However, only constellations with at least 4 stars are kept.
## This is to prevent the constellations from being too small and not being able to be seen.
## Finally, if the constellation was randonly assigned an is_closed = True statement and has at least 3 stars, it adds more more connecting edge to close to the loop.


# --- 3. THE STORYTELLER  --- #

from openai import OpenAI
import random
class AdvancedStoryTeller:
    def __init__(self, api_key, proxy_url):
        self.used_names = set()
        # A list of diverse flavors to guarantee every constellation feels entirely different
        self.themes = [
            "ancient Norse mythology", 
            "forgotten Sumerian folklore", 
            "mystic Aztec legends", 
            "deep-space Sci-Fi traveler lore", 
            "ancient Egyptian religion", 
            "primordial cosmic titan mythos", 
            "Arthurian medieval legend", 
            "oceanic Polynesian navigation lore",
            "dark fantasy cosmic horror"
        ]

## This is the class for the storyteller, it's relatively straightforward.It generates a story for a given constellation.
## It uses the OpenAI API to generate the story and we gave it a list of themes to choose from to give the story something not fully expected. Hopefully not too similar. 
## But it is very cheesy at times. These themes are randomly assigned as well. 

    def generate_myth(self, constellation):
        num_stars = len(constellation.stars)
        chosen_theme = random.choice(self.themes)
        
        prompt = (
            f"You are a cosmic historian. I found a constellation of {num_stars} stars. "
            f"1. Give it a creative, unique proper name inspired by {chosen_theme}. "
            f"2. Write a myth about it. STRICT LIMIT: The story MUST be exactly 3 to 5 sentences maximum. "
            f"Format EXACTLY like this:\n"
            f"Name: [Insert Name]\n"
            f"Story: [Insert Story]"
        )
        
## I think the prompt is pretty funny. We tell it kind of a persona to emulate and then how we want the stories to look like. The sentence maximum was a remnant of the animation code..
## We used to run this code in the terminal, and since later on we tell it to print that every step is done and also print out the stories before the graphic, it would take genuienly 
## ages to get to the graphic, so a small paragraph limit was put in place to speed up the process.

        try:
            response = self.client.chat.completions.create(
                model="GPT-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=150, # Keeps responses short
                timeout=30.0, # Avoid freezing if API is slow or unreachable
            )
            
            text = response.choices[0].message.content
            
            name_line = [line for line in text.split('\n') if line.startswith('Name:')]
            
            try:
                story_part = text.split('Story:')[1].strip()
            except IndexError:
                story_part = "The oracle's scrolls were damaged, and the epic was lost to time."
            
            name = name_line[0].replace('Name:', '').strip() if name_line else f"Sector {constellation.cid} Anomaly"
            
            if name in self.used_names:
                name = f"{name} Major"
            self.used_names.add(name)
            
            return name, story_part
            
        except Exception as e:
            return f"Constellation {constellation.cid}", f"The oracle is silent. (Error: {e})"

    ## This was mainly an error check for us to make sure the storyteller is working fine.
    ## We never saw the 'oracle's scrolls' line, but the 'oracle is silent' line was seen in the early stages of trying to get this code into streamlit.
    ## Ideally, this ensures that the program doesn't crash if the API is slow or unreachable, and then we know exactly where we we wrong depending on what was wrong with the 'oracle'.


# --- 4. ANIMATION FUNCTION --- #

def animate_sky(stars, constellations, interval=50):
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='polar')

    ax.set_facecolor('#000010')
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    
    ax.grid(True, color='cyan', alpha=0.25, linestyle=':') 
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0]) 
    ax.set_yticklabels([]) 
    ax.set_xticks(np.linspace(0, 2*np.pi, 8, endpoint=False))
    ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'], color='#8888AA')

    # Visual Polish: Draw the celestial horizon line
    horizon_angles = np.linspace(0, 2*np.pi, 100)
    ax.plot(horizon_angles, np.ones(100), color='cyan', linestyle='--', alpha=0.3, lw=1)

    initial_az = [s.azimuth for s in stars]
    initial_alt = [s.altitude for s in stars]
    
    sizes = [0.6 * (7 - s.magnitude)**2.5 for s in stars]
    glow_sizes = [s * 4 for s in sizes]
    colors = plt.cm.plasma_r(np.array([s.magnitude for s in stars]) / 6)
    
    scatter_glow = ax.scatter(initial_az, initial_alt, s=glow_sizes, c=colors, alpha=0.2, zorder=9)
    scatter_core = ax.scatter(initial_az, initial_alt, s=sizes, c='white', alpha=0.9, zorder=10)

    const_lines = []
    const_fills = []
    const_labels = []

    for c in constellations:
        line, = ax.plot([], [], color='cyan', lw=2.0, alpha=0.9)
        const_lines.append(line)
        fill, = ax.fill([], [], color='cyan', alpha=0.15)
        const_fills.append(fill)
        
        if len(c.stars) >= 5:
            c_name = c.mythology.split(":")[0] if ":" in c.mythology else f"Constellation {c.cid}"
            center_az, center_alt = c.get_center()
            lbl = ax.text(center_az, center_alt, c_name, color='#AAFFFF', 
                fontsize=9, ha='center', va='center', fontweight='bold',
                bbox=dict(facecolor='#000010', alpha=0.7, edgecolor='none', pad=2), zorder=20)
            const_labels.append((lbl, c))

    time_display = ax.set_title("Simulating Time...", color='white', fontsize=16, fontweight='bold', pad=30)

    start_time_hours = 21.0
    time_step = 0.05

    ## The animate sky function sets up a live animated polar plot that we ended up not fully using but it was easier to make it static for Streamlit later on rather than dealing with it now
    ## The time display ended up not working and wasn't used in the end. But if we had continued with the animation, I think it would have been a very neat add on.
    ## The polar axes are  made so that N at top and goes in the clockwise direction to match a real sky map.
    ## Intially, stars were drawn in two layers: a semi transparent glow scatter adn a smaller bright core that gave a kind of blooming effect to the stars.  

    def update(frame):
        for s in stars:
            s.rotate(time_step)

        new_az = [s.azimuth for s in stars]
        new_alt = [s.altitude for s in stars]
        scatter_core.set_offsets(np.c_[new_az, new_alt])
        scatter_glow.set_offsets(np.c_[new_az, new_alt])

        # Update Constellations
        for i, const in enumerate(constellations):
            c_az = []
            c_alt = []
            
            # Draw the stick-figure branches
            for star1, star2 in const.edges:
                c_az.extend([star1.azimuth, star2.azimuth, np.nan])
                c_alt.extend([star1.altitude, star2.altitude, np.nan])
            
            const_lines[i].set_data(c_az, c_alt)
            
            if const.is_closed:
                fill_az = [s.azimuth for s in const.stars]
                fill_alt = [s.altitude for s in const.stars]
                const_fills[i].set_xy(np.column_stack([fill_az, fill_alt]))
                const_fills[i].set_visible(True) # Turn shading ON
            else:
                const_fills[i].set_visible(False) # Turn shading OFF
            
            c_az_center, c_alt_center = const.get_center()
            const_labels[i][0].set_position((c_az_center, c_alt_center))
            
        for lbl, const in const_labels:
            lbl.set_position(const.get_center())

        current_time = start_time_hours + (frame * time_step)
        current_time_wrapped = current_time % 24 
        hour_24 = int(current_time_wrapped)
        minute = int(round((current_time_wrapped - hour_24) * 60))
        am_pm = "AM" if hour_24 < 12 else "PM"
        hour_12 = hour_24 % 12
        if hour_12 == 0: hour_12 = 12
        time_display.set_text(f"Simulated Time: {hour_12:02d}:{minute:02d} {am_pm}")
        
        return [scatter_core, scatter_glow, time_display] + const_lines + const_fills + [l[0] for l in const_labels]

    ani = FuncAnimation(fig, update, frames=200, interval=interval, blit=False)
    return ani

## The update function is called every interval to update the plot. It rotates the stars and updates the constellations.
## Each frame it rotates every star by a time step of 0.05 hours which is about 3 minutes of simulated time. 
## It redraws every scatter point, all the constellations lines, and shows or hides the cyan fill based on the is_closed command. The cyan fill is a little wonky in Streamlit but I still like it.

def get_static_sky_figure(stars, constellations, time_hours=21.0, name_overrides=None):
    """
    Returns a single-frame matplotlib figure matching animate_sky's look,
    at the given simulated time (hours 0-24). For use in Streamlit (no animation).
    name_overrides: optional dict mapping constellation cid -> display name (e.g. from LLM).
    """
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='polar')

    ax.set_facecolor('#000010')
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)

    ax.grid(True, color='cyan', alpha=0.25, linestyle=':')
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels([])
    ax.set_xticks(np.linspace(0, 2*np.pi, 8, endpoint=False))
    ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'], color='#8888AA')

    horizon_angles = np.linspace(0, 2*np.pi, 100)
    ax.plot(horizon_angles, np.ones(100), color='cyan', linestyle='--', alpha=0.3, lw=1)

    # Rotate stars for this time (same as animate_sky: 15 deg/hour from 21:00)
    rot_rad = (time_hours - 21.0) * (np.pi / 12)
    display_az = np.array([(s.azimuth + rot_rad) % (2*np.pi) for s in stars])
    display_alt = np.array([s.altitude for s in stars])

    sizes = [0.6 * (7 - s.magnitude)**2.5 for s in stars]
    glow_sizes = [s * 4 for s in sizes]
    colors = plt.cm.plasma_r(np.array([s.magnitude for s in stars]) / 6)

    ax.scatter(display_az, display_alt, s=glow_sizes, c=colors, alpha=0.2, zorder=9)
    ax.scatter(display_az, display_alt, s=sizes, c='white', alpha=0.9, zorder=10)

    for c in constellations:
        c_az = []
        c_alt = []
        for star1, star2 in c.edges:
            az1 = (star1.azimuth + rot_rad) % (2*np.pi)
            az2 = (star2.azimuth + rot_rad) % (2*np.pi)
            c_az.extend([az1, az2, np.nan])
            c_alt.extend([star1.altitude, star2.altitude, np.nan])
        ax.plot(c_az, c_alt, color='cyan', lw=2.0, alpha=0.9)
        if getattr(c, 'is_closed', False) and len(c.stars) >= 3:
            fill_az = [(s.azimuth + rot_rad) % (2*np.pi) for s in c.stars]
            fill_alt = [s.altitude for s in c.stars]
            ax.fill(fill_az, fill_alt, color='cyan', alpha=0.15)
        if len(c.stars) >= 5:
            mean_x = np.mean([s.altitude * np.cos((s.azimuth + rot_rad) % (2*np.pi)) for s in c.stars])
            mean_y = np.mean([s.altitude * np.sin((s.azimuth + rot_rad) % (2*np.pi)) for s in c.stars])
            center_az = np.arctan2(mean_y, mean_x)
            center_alt = np.sqrt(mean_x**2 + mean_y**2)
            overrides = name_overrides or {}
            c_name = overrides.get(c.cid) or (c.mythology.split(":")[0] if ":" in c.mythology else f"Constellation {c.cid}")
            ax.text(center_az, center_alt, c_name, color='#AAFFFF', fontsize=9, ha='center', va='center',
                fontweight='bold', bbox=dict(facecolor='#000010', alpha=0.7, edgecolor='none', pad=2), zorder=20)

    current = time_hours % 24
    hour_24 = int(current)
    minute = int(round((current - hour_24) * 60))
    am_pm = "AM" if hour_24 < 12 else "PM"
    hour_12 = hour_24 % 12 or 12
    ax.set_title(f"Simulated Time: {hour_12:02d}:{minute:02d} {am_pm}", color='white', fontsize=16, fontweight='bold', pad=30)

    plt.tight_layout()
    return fig

## The get_static_sky_figure function is used to create a static figure, that static image that is shown is used in streamlit because we were not able to figure out how to animate in Streamlit.
## It is basically the same as the animate_sky function but without the animation.
## It doesn't change any of the star objects so we can keep all of the code that we had before.
## It uses a name_overrides dictionary so that Streamlit can use the LLM generated names without permanently modyfinging the constellation objects.


# --- 5. FILE I/O WITH ERROR HANDLING --- #

def save_universe(filename, stars, constellations):
    """Saves universe with error handling for file permissions or empty data."""
    if not stars or not constellations:
        print("Error: Attempted to save an empty universe.")
        return

    try:
        data = {
            "stars": [s.to_dict() for s in stars],
            "constellations": [c.to_dict() for c in constellations]
        }
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Universe successfully saved to {filename}")
    except (IOError, PermissionError) as e:
        print(f"CRITICAL ERROR: Could not save file. Technical details: {e}")

## save universe turns the star fields and constellations into a JSON file using each object's to_dict method. 
## This prevents two main things, saving an unworking/empty universe and also allows us to load the universe back in later if we want to.
## Errors like permission errors or file not found errors are caught and printed out to the console so we know where this is going wrong.


# # --- MAIN EXECUTION --- # #

if __name__ == "__main__":

    print("--- STEP 1: GENESIS ---")
    sky = generate_stars(num_stars=600, seed=None) 
    print(f"Created {len(sky)} stars.")

    print("\n--- STEP 2: CLUSTERING ---")
    patterns = create_constellations(sky, max_distance=0.35, min_spacing=0.15)
    print(f"Discovered {len(patterns)} constellations.")

## these first two steps are printed to make sure that the code is working and that the stars and constellations are being created.

    print("\n--- STEP 3: MYTHOLOGY (CONSULTING THE ORACLE) ---")
    # Use environment variable (never commit keys to the repo)
    my_api_key = os.getenv("ASTRO1221_API_KEY") or os.getenv("OSU_LITELLM_API_KEY")
    my_proxy_url = os.getenv("ASTRO1221_PROXY_URL") or os.getenv("OSU_LITELLM_PROXY_URL") or "https://litellmproxy.osu-ai.org/v1"

    if not my_api_key:
        print("ERROR: No API key found. Set ASTRO1221_API_KEY or OSU_LITELLM_API_KEY in your environment.")
        print("  Windows (PowerShell): $env:ASTRO1221_API_KEY = \"your-key-here\"")
        print("  Or add to .streamlit/secrets.toml: osu_litellm_api_key = \"your-key-here\"")
        print("Skipping LLM mythology — using placeholder names only.")
        oracle = None
    else:
        oracle = AdvancedStoryTeller(api_key=my_api_key, proxy_url=my_proxy_url)
    
    print(f"Generating lore for the MAJOR constellations only. This will be much faster...")
    
    for i, p in enumerate(patterns):
        if len(p.stars) >= 5 and oracle:
            print(f"  Dreaming up Major Constellation #{p.cid}...")
            name, story = oracle.generate_myth(p)
            p.mythology = f"{name}: {story}"
            print(f"   -> {name}\n   -> {story}\n")
        elif len(p.stars) >= 5:
            p.mythology = f"Major Sector {p.cid} Anomaly: A faint, uncharted cluster."
        else:
            p.mythology = f"Minor Sector {p.cid} Anomaly: A faint, uncharted cluster."

## The print for step 3 is a little more descriptive and tells us which constellation is being worked on and what the story is.
## If ran in the terminal, it would print out the story for each constellation. Which was one of the things that I talked about eariler. The time that it took to run this code with this steps was very long,
## We made sure to imbed a few error statements to make sure that the code is working fine and that the API is working fine. Depending on the error, we would know exactly where we went wrong.


    print("\n--- STEP 4: LIVE ANIMATION ---")
    print("Opening Window... Close the window to save and exit.")
    
    my_anim = animate_sky(sky, patterns, interval=50)
    
    plt.tight_layout()
    plt.show()

    print("\n--- STEP 5: SAVING ---")
    save_universe("my_constellation_system.json", sky, patterns)
    print("Done!")

## And the last two steps are just creating the animation and saving the universe. It will give you a 'Done!' if all of these steps have been satisfied.
## That is all for the code that goes into the streamlit app! We have another code file that runs the app that has more description of what's going on over there.
## Thank you! :)