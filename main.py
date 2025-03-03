import streamlit as st
import streamlit_option_menu
from streamlit_extras.stoggle import stoggle
from processing import preprocess
from processing.display import Main
import requests
import os
import json
from urllib.parse import urlencode, quote_plus
import base64
import time
import uuid

# Setting the wide mode as default
st.set_page_config(layout="wide")

displayed = []

# Initialize session state
st.session_state.setdefault('movie_number', 25)
st.session_state.setdefault('selected_movie_name', "")
st.session_state.setdefault('user_menu', "")
st.session_state.setdefault('is_authenticated', False)
st.session_state.setdefault('user_info', None)
st.session_state.setdefault('access_token', None)
st.session_state.setdefault('id_token', None)
st.session_state.setdefault('refresh_token', None)
st.session_state.setdefault('token_expiry', 0)

# Auth0 configuration - Replace with your actual Auth0 credentials
AUTH0_CLIENT_ID = ''
AUTH0_CLIENT_SECRET = ''
AUTH0_DOMAIN = 'dev-n74s8t8mk10d1xss.us.auth0.com'
AUTH0_CALLBACK_URL = 'http://localhost:8501/callback'
AUTH0_LOGOUT_URL = f'https://{AUTH0_DOMAIN}/v2/logout'


def generate_auth_url():
    """Generate Auth0 authorization URL"""
    params = {
        'client_id': AUTH0_CLIENT_ID,
        'redirect_uri': AUTH0_CALLBACK_URL,
        'response_type': 'code',
        'scope': 'openid profile email offline_access',
        'state': str(uuid.uuid4()),
    }
    auth_url = f'https://{AUTH0_DOMAIN}/authorize?{urlencode(params)}'
    return auth_url


def exchange_code_for_token(code):
    """Exchange authorization code for tokens"""
    token_url = f'https://{AUTH0_DOMAIN}/oauth/token'
    payload = {
        'grant_type': 'authorization_code',
        'client_id': AUTH0_CLIENT_ID,
        'client_secret': AUTH0_CLIENT_SECRET,
        'code': code,
        'redirect_uri': AUTH0_CALLBACK_URL
    }
    response = requests.post(token_url, json=payload)
    
    if response.status_code == 200:
        tokens = response.json()
        st.session_state.access_token = tokens.get('access_token')
        st.session_state.id_token = tokens.get('id_token')
        st.session_state.refresh_token = tokens.get('refresh_token')
        st.session_state.token_expiry = time.time() + tokens.get('expires_in', 86400)
        st.session_state.is_authenticated = True
        
        # Get user info
        user_info = get_user_info(st.session_state.access_token)
        st.session_state.user_info = user_info
    else:
        st.error(f"Failed to exchange code for token: {response.text}")


def get_user_info(access_token):
    """Get user information from Auth0"""
    url = f'https://{AUTH0_DOMAIN}/userinfo'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to get user info: {response.text}")
        return None


def refresh_access_token():
    """Refresh the access token using the refresh token"""
    if not st.session_state.refresh_token:
        st.session_state.is_authenticated = False
        return False
    
    token_url = f'https://{AUTH0_DOMAIN}/oauth/token'
    payload = {
        'grant_type': 'refresh_token',
        'client_id': AUTH0_CLIENT_ID,
        'client_secret': AUTH0_CLIENT_SECRET,
        'refresh_token': st.session_state.refresh_token
    }
    
    response = requests.post(token_url, json=payload)
    
    if response.status_code == 200:
        tokens = response.json()
        st.session_state.access_token = tokens.get('access_token')
        st.session_state.id_token = tokens.get('id_token')
        st.session_state.token_expiry = time.time() + tokens.get('expires_in', 86400)
        return True
    else:
        st.session_state.is_authenticated = False
        return False


def check_token_validity():
    """Check if token is valid and refresh if needed"""
    if not st.session_state.is_authenticated:
        return False
    
    # If token is about to expire in the next 5 minutes, refresh it
    if st.session_state.token_expiry - time.time() < 300:
        return refresh_access_token()
    
    return True


def logout():
    """Log out the user from Auth0"""
    # Clear session state
    st.session_state.is_authenticated = False
    st.session_state.user_info = None
    st.session_state.access_token = None
    st.session_state.id_token = None
    st.session_state.refresh_token = None
    st.session_state.token_expiry = 0
    
    # Redirect to Auth0 logout
    params = {
        'client_id': AUTH0_CLIENT_ID,
        'returnTo': 'http://localhost:8501'
    }
    logout_url = f"{AUTH0_LOGOUT_URL}?{urlencode(params)}"
    st.markdown(f'<meta http-equiv="refresh" content="0;url={logout_url}">', unsafe_allow_html=True)


def handle_authentication():
    """Handle the authentication process"""
    # Check for callback
    query_params = st.query_params
    
    if 'code' in query_params:
        code = query_params['code']
        # Exchange code for token
        exchange_code_for_token(code)
        # Clear the URL parameters
        st.query_params.clear()
        st.rerun()
    
    # Check token validity
    if st.session_state.is_authenticated:
        valid = check_token_validity()
        if not valid:
            auth_url = generate_auth_url()
            st.warning("Your session has expired. Please log in again.")
            st.link_button("Log In", auth_url)
            return False
        return True
    
    # Not authenticated, show login button
    auth_url = generate_auth_url()
    st.title("🎬 Movie Recommender")
    st.write("Please log in to access the movie recommender system.")
    st.link_button("Log In with Auth0", auth_url)
    return False


def main():
    # First, handle authentication
    if not handle_authentication():
        return
    
    # If authenticated, show the user info and logout button
    with st.sidebar:
        st.markdown("## 🎬 Movie Recommender")
        if st.session_state.user_info:
            st.write(f"Welcome, {st.session_state.user_info.get('name', 'User')}!")
            if 'picture' in st.session_state.user_info:
                st.image(st.session_state.user_info['picture'], width=50)
            if st.button("Logout"):
                logout()

    def initial_options():
        # Vertical menu in the sidebar
        with st.sidebar:
            st.session_state.user_menu = streamlit_option_menu.option_menu(
                menu_title=None,  # no header since we have our own markdown
                options=[
                    "Recommend me a similar movie",
                    "Describe me a movie",
                    "Check all Movies",
                    "My Favorites"  # New option for authenticated users
                ],
                icons=["film", "info-circle", "grid-3x3", "heart"],
                menu_icon="cast",
                default_index=0,
                orientation="vertical",
            )

        # Dispatch to the right view
        if st.session_state.user_menu == "Recommend me a similar movie":
            recommend_display()
        elif st.session_state.user_menu == "Describe me a movie":
            display_movie_details()
        elif st.session_state.user_menu == "My Favorites":
            display_favorites()
        else:  # "Check all Movies"
            paging_movies()

    def recommend_display():
        st.title("Movie Recommender System")
        selected_movie_name = st.selectbox(
            "Select a Movie...", new_df["title"].values
        )
        if st.button("Recommend"):
            st.session_state.selected_movie_name = selected_movie_name
            recommendation_tags(new_df, selected_movie_name,
                                r"Files/similarity_tags_tags.pkl", "are")
            recommendation_tags(new_df, selected_movie_name,
                                r"Files/similarity_tags_genres.pkl", "on the basis of genres are")
            recommendation_tags(new_df, selected_movie_name,
                                r"Files/similarity_tags_tprduction_comp.pkl", "from the same production company are")
            recommendation_tags(new_df, selected_movie_name,
                                r"Files/similarity_tags_keywords.pkl", "on the basis of keywords are")
            recommendation_tags(new_df, selected_movie_name,
                                r"Files/similarity_tags_tcast.pkl", "on the basis of cast are")

    def recommendation_tags(df, movie_name, pickle_path, desc):
        movies, posters = preprocess.recommend(df, movie_name, pickle_path)
        st.subheader(f"Best recommendations {desc}...")
        rec_movies, rec_posters = [], []
        for m, p in zip(movies, posters):
            if len(rec_movies) == 5:
                break
            if m not in displayed:
                rec_movies.append(m)
                rec_posters.append(p)
                displayed.append(m)

        cols = st.columns(5)
        for col, title, poster in zip(cols, rec_movies, rec_posters):
            with col:
                st.text(title)
                st.image(poster)
                if st.button(f"❤️", key=f"fav_{title}"):
                    add_to_favorites(title)

    def display_movie_details():
        st.title("Movie Details")

        # Let the user choose which movie to describe
        movie_name = st.selectbox(
            "Select a movie to describe:",
            new_df["title"].values,
            index=0,
            key="describe_selectbox"
        )
        # Persist selection
        st.session_state.selected_movie_name = movie_name

        # Now safe to fetch details
        info = preprocess.get_details(movie_name)

        with st.container():
            image_col, text_col = st.columns((1, 2))
            with image_col:
                st.image(info[0])
                if st.button("Add to Favorites"):
                    add_to_favorites(movie_name)

            with text_col:
                st.title(movie_name)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Rating", info[8])
                with col2:
                    st.metric("No. of ratings", info[9])
                with col3:
                    st.metric("Runtime", f"{info[6]} min")

                st.markdown("**Overview**")
                st.write(info[3])

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Release Date:** {info[4]}")
                with col2:
                    st.markdown(f"**Budget:** ${info[1]:,}")
                with col3:
                    st.markdown(f"**Revenue:** ${info[5]:,}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("**Genres:** " + " · ".join(info[2]))
                with col2:
                    st.markdown("**Available in:** " + " · ".join(info[13]))
                with col3:
                    st.markdown("**Directed by:** " + info[12][0])

        st.header("Cast")
        urls, bios = [], []
        for pid in info[14][:5]:
            url, bio = preprocess.fetch_person_details(pid)
            urls.append(url)
            bios.append(bio)

        cols = st.columns(5)
        for col, u, b in zip(cols, urls, bios):
            with col:
                st.image(u)
                stoggle("Show More", b)

    def paging_movies():
        max_pages = len(movies) // 10
        col_prev, col_slider, col_next = st.columns([1, 9, 1])

        with col_prev:
            if st.button("Prev") and st.session_state.movie_number >= 10:
                st.session_state.movie_number -= 10

        with col_slider:
            pg = st.slider("Page", 0, max_pages, st.session_state.movie_number // 10)
            st.session_state.movie_number = pg * 10

        with col_next:
            if st.button("Next") and st.session_state.movie_number + 10 < len(movies):
                st.session_state.movie_number += 10

        display_all_movies(st.session_state.movie_number)

    def display_all_movies(start):
        i = start
        for _ in range(2):  # two rows
            cols = st.columns(5)
            for col in cols:
                m_id = movies.iloc[i]["movie_id"]
                poster = preprocess.fetch_posters(m_id)
                col.image(poster, caption=movies.iloc[i]["title"])
                # Add favorite button
                if col.button("❤️", key=f"fav_all_{movies.iloc[i]['title']}"):
                    add_to_favorites(movies.iloc[i]["title"])
                i += 1

    def get_user_favorites():
        """Get user's favorite movies from Auth0 metadata"""
        if not st.session_state.is_authenticated or not st.session_state.user_info:
            return []
        
        # Get user ID from Auth0
        user_id = st.session_state.user_info.get('sub')
        if not user_id:
            return []
        
        # In a real app, you would fetch this from a database or Auth0 metadata
        # For now, we'll use session state as a simple store
        if 'favorites' not in st.session_state:
            st.session_state.favorites = {}
        
        if user_id not in st.session_state.favorites:
            st.session_state.favorites[user_id] = []
            
        return st.session_state.favorites[user_id]

    def add_to_favorites(movie_name):
        """Add a movie to user's favorites"""
        if not st.session_state.is_authenticated:
            st.warning("Please log in to add favorites")
            return
        
        # Get user ID from Auth0
        user_id = st.session_state.user_info.get('sub')
        if not user_id:
            st.warning("User ID not found")
            return
        
        # In a real app, you would store this in a database or Auth0 metadata
        if 'favorites' not in st.session_state:
            st.session_state.favorites = {}
        
        if user_id not in st.session_state.favorites:
            st.session_state.favorites[user_id] = []
            
        if movie_name not in st.session_state.favorites[user_id]:
            st.session_state.favorites[user_id].append(movie_name)
            st.success(f"Added '{movie_name}' to your favorites!")
        else:
            st.info(f"'{movie_name}' is already in your favorites!")

    def remove_from_favorites(movie_name):
        """Remove a movie from user's favorites"""
        user_id = st.session_state.user_info.get('sub')
        if user_id and 'favorites' in st.session_state and user_id in st.session_state.favorites:
            if movie_name in st.session_state.favorites[user_id]:
                st.session_state.favorites[user_id].remove(movie_name)
                st.success(f"Removed '{movie_name}' from your favorites!")
                st.rerun()

    def display_favorites():
        """Display user's favorite movies"""
        st.title("My Favorite Movies")
        
        favorites = get_user_favorites()
        if not favorites:
            st.info("You haven't added any favorite movies yet!")
            return
        
        # Display favorites in a grid
        cols = st.columns(5)
        for i, movie_name in enumerate(favorites):
            col = cols[i % 5]
            with col:
                # Find movie in dataframe
                movie_row = new_df[new_df["title"] == movie_name]
                if not movie_row.empty:
                    movie_id = movie_row.iloc[0]["id"] if "id" in movie_row.columns else None
                    if movie_id:
                        poster = preprocess.fetch_posters(movie_id)
                        st.image(poster, caption=movie_name)
                    else:
                        st.text(movie_name)
                else:
                    st.text(movie_name)
                
                if st.button("Remove", key=f"remove_{movie_name}"):
                    remove_from_favorites(movie_name)

    # Load data & show menu
    with Main() as bot:
        bot.main_()
        new_df, movies, movies2 = bot.getter()
    initial_options()


if __name__ == "__main__":
    main()