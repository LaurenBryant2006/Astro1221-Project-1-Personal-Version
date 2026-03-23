"""
Streamlit app: sky map using the animate_sky-style figure from CodeForStreamlit1.
Select a constellation (click equivalent) to show the LLM Storyteller mythology in a box below.
Run with: streamlit run "Random Constellation Generator App.py"
"""
# This file is the main file that runs the streamlit app/site. It is separate from the others to keep it neat. We first imported the necessary libraries, and the code from the other file. Then there are definitions that create the interactive and visual elements of the site. Lastly, the main function that runs the app. The goal was to create an interactive constellation generator with the ability to generate mythology and names for the constellations. It was important to us that the sky map was round like a real sky map.

# 1. Here we import the libraries we need. Importlib.util is used to load the code from the other coding file. Sys is used to close the app if there is an error. Path helps find the other file. Os is used to get the api key from the secret file. Matplotlib is to make the sky map. Lastly, streamlit makes the website/app.
import importlib.util
import sys
from pathlib import Path
from importlib.machinery import SourceFileLoader

import os

import matplotlib.pyplot as plt
import streamlit as st

# This is a failsafe that allows the site to run even if the api key is not found. (The LLM will not connect however the sky map will still show and generate the constellations.)
try:
    from streamlit.errors import StreamlitSecretNotFoundError
except ImportError:
    StreamlitSecretNotFoundError = Exception  # older Streamlit

# This function uses the pathlib import to find the code in the file CodeForStreamlit1.
SCRIPT_DIR = Path(__file__).resolve().parent
for name in ("CodeForStreamlit1", "CodeForStreamlit1.py"):
    code_path = SCRIPT_DIR / name
    if code_path.exists():
        break
else:
    code_path = SCRIPT_DIR / "CodeForStreamlit1"

# Here these functions use importlib.machinery to load in the code from the other file which helps ensure it runs correctly..
loader = SourceFileLoader("code_for_streamlit", str(code_path))
spec = importlib.util.spec_from_loader("code_for_streamlit", loader)
code_module = importlib.util.module_from_spec(spec)
sys.modules["code_for_streamlit"] = code_module
spec.loader.exec_module(code_module)

# This calls over the specific functions needed from the other file to create the site.
generate_stars = code_module.generate_stars
create_constellations = code_module.create_constellations
get_static_sky_figure = code_module.get_static_sky_figure
AdvancedStoryTeller = code_module.AdvancedStoryTeller


# 2. Now we start creating the definitions that will generat the visuals and interactive elements of the site.

# This is the function that generates the stars and constellations calling back to functions in the other file.
@st.cache_data
def get_universe(seed=None, num_stars=400):
    """Generate stars and constellations once."""
    stars = generate_stars(num_stars=num_stars, seed=seed)
    constellations = create_constellations(stars, max_distance=0.35, min_spacing=0.15)
    # Assign placeholder mythology so labels show "Constellation N" until LLM is used
    for c in constellations:
        if not c.mythology or c.mythology == "Unknown":
            c.mythology = f"Constellation {c.cid}: (click to generate myth)"
    return stars, constellations


# this is the function that displays the name of the constellation in the dropdown.
def _constellation_label(c, mythology_cache):
    """Display name for dropdown: from cache if generated, else Constellation N."""
    if c.cid in mythology_cache:
        return mythology_cache[c.cid].get("name") or f"Constellation {c.cid}"
    return f"Constellation {c.cid}"


# This is the main function that has the visuals for the app.
def main():
    st.set_page_config(page_title="Sky Map", page_icon="🌌", layout="centered")
    st.title("Random Sky Map Generator: Constellations & Mythology")
    st.markdown(
        "Created by Lauren Bryant and Ithea Engum-Corral. The sky map below generates a random set of constellations. Use the seed to randomly generate new layout. Use the slider to change the amount of stars. "
        "**Select a constellation** from the dropdown under the map to see the name and mythology."
    )
    # this is the session that stores the mythology cache and the storyteller llm. To get the api key there is a secrets file where it is stored. This section also retrieves it from there.
    if "mythology_cache" not in st.session_state:
        st.session_state.mythology_cache = {}
    if "storyteller" not in st.session_state:
        api_key = ""
        proxy_url = "https://litellmproxy.osu-ai.org/v1"
        try:
            api_key = st.secrets.get("osu_litellm_api_key", "") or st.secrets.get("api_key", "")
            proxy_url = st.secrets.get("osu_litellm_proxy_url", proxy_url)
        except StreamlitSecretNotFoundError:
            pass
        if not api_key:
            api_key = os.environ.get("OSU_LITELLM_API_KEY", "")
        st.session_state.storyteller = None
        st.session_state.storyteller_api_key = api_key
        st.session_state.storyteller_proxy_url = proxy_url

    # Here we create interactive seed bar and the star slider by calling to streamlit..
    seed = st.sidebar.number_input("Random seed", min_value=0, value=42, step=1)
    num_stars = st.sidebar.slider("Number of stars", 100, 600, 400, 50)

    with st.spinner("Generating star field…"):
        stars, constellations = get_universe(seed=seed, num_stars=num_stars)

    time_hours = 21.0  # Fixed simulated time (9 PM)

    # This overrides the LLM name so the map shows constellation names once generated
    mythology_cache = st.session_state.mythology_cache
    name_overrides = {cid: mythology_cache[cid]["name"] for cid in mythology_cache if mythology_cache[cid].get("name")}

    # This creates the static frame of animate_sky.
    fig = get_static_sky_figure(stars, constellations, time_hours=time_hours, name_overrides=name_overrides)
    st.pyplot(fig)
    plt.close(fig)

    # Here we import the streamlit functions to create the dropdown mythology box and choose the text that will appear.
    st.subheader("Select a constellation")
    selected_index = st.selectbox(
        "Choose a constellation to view its mythology ",
        options=range(len(constellations)),
        format_func=lambda i: _constellation_label(constellations[i], mythology_cache),
        index=0,
        key="const_select",
    )
    selected_cid = constellations[selected_index].cid

    # This function generates the mythology for the selected constellation.
    if selected_cid is not None:
        selected_const = next((c for c in constellations if c.cid == selected_cid), None)
        if selected_const is not None and selected_cid not in mythology_cache:
            api_key = st.session_state.storyteller_api_key
            proxy_url = st.session_state.storyteller_proxy_url
            if api_key:
                if st.session_state.storyteller is None:
                    st.session_state.storyteller = AdvancedStoryTeller(api_key=api_key, proxy_url=proxy_url)
                with st.spinner("Asking the Storyteller for this constellation's myth…"):
                    name, story = st.session_state.storyteller.generate_myth(selected_const)
                    st.session_state.mythology_cache[selected_cid] = {"name": name, "story": story}
                    selected_const.mythology = f"{name}: {story}"
                    st.session_state.just_discovered = selected_cid

    # This calls to streamlit and creates the mythology box under the sky map, and if the api key is not found, will prompt to set it. Here as it checks the cache, it uses the if/elif statements to determine if it will show the "new discovery" line or not.
    st.markdown("---")
    if selected_cid is not None and selected_cid in mythology_cache:
        cached = mythology_cache[selected_cid]
        name = cached.get("name", f"Constellation {selected_cid}")
        story = cached.get("story", "")
        if st.session_state.get("just_discovered") == selected_cid:
            st.success("New Discovery!")
            st.session_state.just_discovered = None
        st.subheader(f"📜 {name}")
        st.info(story)
    elif selected_cid is not None:
        st.info(
            "Set your OSU LiteLLM API key in `.streamlit/secrets.toml` (e.g. `osu_litellm_api_key`) "
            "or in the environment as `OSU_LITELLM_API_KEY` to generate mythology for this constellation."
        )
    else:
        st.caption("Select a constellation above to see its mythology here.")


# 3. This is the main function that runs the app. It checks if the app is being run in streamlit, and if not, will run the command.
if __name__ == "__main__":
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is None:
            raise RuntimeError("Not in Streamlit")
        main()
    except Exception:
        import subprocess
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve()), *sys.argv[1:]])
