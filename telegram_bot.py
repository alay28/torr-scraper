import random
import requests
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from scraper import fetch_magnet_links

# TVmaze API Base URL
TVMAZE_API_BASE = "https://api.tvmaze.com"

# Meme URL
meme_url = "https://indianmemetemplates.com/wp-content/uploads/ruko-zara-sabar-karo.jpg"

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Movie", callback_data="type_movie")],
        [InlineKeyboardButton("Series", callback_data="type_series")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("What are you looking for?", reply_markup=reply_markup)

# Handle user choice between Movie and Series
async def handle_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "type_movie":
        context.user_data["search_type"] = "movie"
        await query.edit_message_text("Great! Please enter the movie name.")
    elif query.data == "type_series":
        context.user_data["search_type"] = "series"
        await query.edit_message_text("Great! Please enter the series name.")

# Handle user input for Movie or Series
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_input = update.message.text
    search_type = context.user_data.get("search_type")

    if search_type == "movie":
        await handle_movie_search(update, user_input)
    elif search_type == "series":
        await handle_series_search(update, user_input, context)
    else:
        await update.message.reply_text("Please select Movie or Series first using /start.")

# Function to send the meme during search
async def send_meme(update: Update):
    # Ensure that the update contains a valid message
    if update.message:
        meme_url = "https://example.com/meme.jpg"  # Replace with your actual meme URL
        await update.message.reply_photo(meme_url, caption="Ruko Zara... Sabar Karo! Searching for your request...")
    else:
        # Log or handle the case where update.message is None
        print(f"Update does not contain a message: {update}")
        
# Handle movie search
async def handle_movie_search(update: Update, movie_name: str) -> None:
    # Send meme first

    # Start actual search
    start_time = time.time()
    await send_meme(update)
    magnet_link = fetch_magnet_links(movie_name)
    end_time = time.time()

    total_time = end_time - start_time
    if magnet_link:
        await update.message.reply_text(f"Magnet link retrieved successfully:\n\n{magnet_link}")
        await update.message.reply_text(f"Execution time: {total_time:.2f} seconds")
    else:
        await update.message.reply_text(f"Failed to retrieve a magnet link for '{movie_name}'.")
        await update.message.reply_text(f"Execution time: {total_time:.2f} seconds")

# Handle series search
async def handle_series_search(update: Update, series_name: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Send meme first

    # Start actual search
    user_input = update.message.text
    context.user_data["series_name"] = user_input
    response = requests.get(f"{TVMAZE_API_BASE}/search/shows?q={series_name}")
    if response.status_code == 200 and response.json():
        series = response.json()[0]["show"]
        series_id = series["id"]
        series_name = series["name"]

        seasons_response = requests.get(f"{TVMAZE_API_BASE}/shows/{series_id}/seasons")
        if seasons_response.status_code == 200:
            seasons = seasons_response.json()

            keyboard = [
                [InlineKeyboardButton(f"Season {season['number']}", callback_data=f"season_{season['id']}")]
                for season in seasons
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(f"Select a season for {series_name}:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("Failed to fetch seasons. Please try again.")
    else:
        await update.message.reply_text("Series not found. Please check the name and try again.")

# Handle season selection
async def handle_season_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    season_id = query.data.split("_")[1]

    response = requests.get(f"{TVMAZE_API_BASE}/seasons/{season_id}/episodes")
    if response.status_code == 200:
        episodes = response.json()

        # Create a separate button for downloading the entire season
        download_button = [InlineKeyboardButton("Download Entire Season", callback_data=f"download_season_{season_id}")]

        # Create buttons for each episode
        episode_buttons = [
            [InlineKeyboardButton(f"{episode['number']}. {episode['name']}", callback_data=f"episode_{episode['id']}")]
            for episode in episodes
        ]

        # Combine the buttons
        keyboard = [download_button] + episode_buttons
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Select an episode or download the entire season:", reply_markup=reply_markup)

    else:
        await query.edit_message_text("Failed to fetch episodes. Please try again.")

# Handle entire season download
async def handle_entire_season_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    season_id = query.data.split("_")[2]

    # Fetch season details for constructing search query
    response = requests.get(f"{TVMAZE_API_BASE}/seasons/{season_id}")
    if response.status_code == 200:
        season_data = response.json()
        # Use the user-provided series name
        series_name = context.user_data.get("series_name", "Unknown Series")
        season_number = season_data["number"]

        # Construct a search query specific to the series and season
        search_query = f"{series_name} Season {season_number}"
        await query.edit_message_text(f"Searching for: {search_query}")

        # Fetch magnet link for the entire season
        start_time = time.time()
        await send_meme(update)

        magnet_link = fetch_magnet_links(search_query, season_number=season_number)
        end_time = time.time()

        total_time = end_time - start_time
        if magnet_link:
            await query.message.reply_text(f"Magnet link retrieved successfully:\n\n{magnet_link}")
            await query.message.reply_text(f"Execution time: {total_time:.2f} seconds")
        else:
            await query.message.reply_text(f"Failed to retrieve a magnet link for '{search_query}'.")
            await query.message.reply_text(f"Execution time: {total_time:.2f} seconds")
    else:
        await query.edit_message_text("Failed to fetch season details. Please try again.")

# Handle episode selection
async def handle_episode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    episode_id = query.data.split("_")[1]

    response = requests.get(f"{TVMAZE_API_BASE}/episodes/{episode_id}")
    if response.status_code == 200:
        episode = response.json()
        series_name = episode["name"]
        season_number = episode["season"]
        episode_number = episode["number"]

        search_query = f"{series_name} S{season_number:02d}E{episode_number:02d}"

        keyboard = [
            [InlineKeyboardButton("720p", callback_data=f"quality_720p_{search_query}"),
             InlineKeyboardButton("1080p", callback_data=f"quality_1080p_{search_query}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Select quality:", reply_markup=reply_markup)
    else:
        await query.edit_message_text("Failed to fetch episode details. Please try again.")

# Handle quality selection
async def handle_quality_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    quality = data[1]
    search_query = data[2]

    search_query_with_quality = f"{search_query} {quality}"
    start_time = time.time()
    await send_meme(update)
    magnet_link = fetch_magnet_links(search_query_with_quality)
    end_time = time.time()

    total_time = end_time - start_time
    if magnet_link:
        await query.message.reply_text(f"{magnet_link}")
        await query.message.reply_text(f"Execution time: {total_time:.2f} seconds")
    else:
        await query.message.reply_text(f"Failed to retrieve a magnet link for '{search_query_with_quality}'.")
        await query.message.reply_text(f"Execution time: {total_time:.2f} seconds")

# Main function to set up the bot
def main():
    application = Application.builder().token("7544691193:AAF5yPc_JN1ptm8gPJrUnO0jn661p3v5cL0").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_type_selection, pattern="^type_"))
    application.add_handler(CallbackQueryHandler(handle_season_selection, pattern="^season_"))
    application.add_handler(CallbackQueryHandler(handle_entire_season_download, pattern="^download_season_"))
    application.add_handler(CallbackQueryHandler(handle_episode_selection, pattern="^episode_"))
    application.add_handler(CallbackQueryHandler(handle_quality_selection, pattern="^quality_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()
    
if __name__ == "__main__":
    main()
