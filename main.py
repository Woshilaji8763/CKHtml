import asyncio
import aiohttp
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = "8395763661:AAEVpKtmA1C9qw15bQUMnUaHVG_rjo6_6C0"
CHANNEL_ID = "-1002180212216"
ADMIN_ID = None  # Will be set when admin starts bot

# API configurations
API_CONFIGS = {
    'mzplay': {
        'name': 'MZPlay',
        'type_id': 30,
        'interval': 30,
        'register_link': 'https://mz155.com/#/register?invitationCode=24667538788',
        'period_api': 'https://mzplayapi.com/api/webapi/GetGameIssue',
        'history_api': 'https://mzplayapi.com/api/webapi/GetNoaverageEmerdList'
    },
    'mysgame': {
        'name': 'MysGame', 
        'type_id': 1,
        'interval': 60,
        'register_link': 'https://myslotto.net/#/register?invitationCode=28487236736',
        'period_api': 'https://mzplayapi.com/api/webapi/GetGameIssue',
        'history_api': 'https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json'
    }
}

class GameSettings:
    def __init__(self):
        self.total_games = 100
        self.current_game = 0
        self.wins = 0
        self.losses = 0
        self.current_streak = 0
        self.longest_win_streak = 0
        self.longest_loss_streak = 0
        self.is_win_streak = True
        self.bet_amount = 1
        self.base_bet_amount = 1
        self.current_platform = 'mysgame'
        self.current_mode = 'sureshot'
        self.bot_running = False
        self.message_history = {'mzplay': [], 'mysgame': []}
        self.prediction_history = {'mzplay': [], 'mysgame': []}
        self.last_processed_period = {'mzplay': None, 'mysgame': None}

# Global game settings
game_settings = GameSettings()

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()

def get_all_users() -> List[int]:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

# Prediction algorithms
def calculate_prediction(numbers: List[int]) -> Dict:
    """Enhanced prediction algorithm with multiple methods"""
    target_numbers = [numbers[2], numbers[3], numbers[4]]
    
    # Method 1: Enhanced Addition with pattern analysis
    sum_result = sum(target_numbers)
    add_result = sum_result
    add_steps = [f"{target_numbers[0]} + {target_numbers[1]} + {target_numbers[2]} = {sum_result}"]
    
    while add_result > 9:
        digits = [int(d) for d in str(add_result)]
        new_sum = sum(digits)
        add_steps.append(f"{add_result} → {' + '.join(map(str, digits))} = {new_sum}")
        add_result = new_sum
    
    # Method 2: Enhanced Subtraction
    diff = abs(target_numbers[0] - target_numbers[1] - target_numbers[2])
    diff_steps = [f"|{target_numbers[0]} - {target_numbers[1]} - {target_numbers[2]}| = {diff}"]
    
    sub_result = diff
    while sub_result > 9:
        digits = [int(d) for d in str(sub_result)]
        new_sum = sum(digits)
        diff_steps.append(f"{sub_result} → {' + '.join(map(str, digits))} = {new_sum}")
        sub_result = new_sum
    
    # Method 3: Pattern Recognition
    recent_numbers = numbers[:7]
    big_count = len([n for n in recent_numbers if n >= 5])
    small_count = len([n for n in recent_numbers if n <= 4])
    last_three = numbers[:3]
    consecutive_big = all(n >= 5 for n in last_three)
    consecutive_small = all(n <= 4 for n in last_three)
    
    # Method 4: Fibonacci-based calculation
    fib_mod = (target_numbers[0] + target_numbers[1] * 2 + target_numbers[2] * 3) % 10
    
    # Method 5: Prime number analysis
    primes = [2, 3, 5, 7]
    prime_sum = len([n for n in target_numbers if n in primes])
    prime_result = 'SMALL' if prime_sum % 2 == 0 else 'BIG'
    
    # Enhanced prediction logic
    enhanced_add_prediction = 'BIG' if add_result >= 5 else 'SMALL'
    enhanced_sub_prediction = 'BIG' if sub_result >= 5 else 'SMALL'
    
    # Pattern-based adjustments
    if consecutive_big and big_count >= 5:
        enhanced_add_prediction = 'SMALL'  # Reverse pattern
    elif consecutive_small and small_count >= 5:
        enhanced_add_prediction = 'BIG'  # Reverse pattern
    
    # Weighted decision algorithm
    methods = {
        'addition': enhanced_add_prediction,
        'subtraction': enhanced_sub_prediction,
        'pattern': 'SMALL' if big_count > small_count else 'BIG',  # Reverse psychology
        'fibonacci': 'BIG' if fib_mod >= 5 else 'SMALL',
        'prime': prime_result
    }
    
    # Vote-based final prediction
    votes = list(methods.values())
    big_votes = votes.count('BIG')
    small_votes = votes.count('SMALL')
    
    # Final enhanced predictions
    final_add_prediction = 'BIG' if big_votes > small_votes else 'SMALL'
    final_sub_prediction = enhanced_sub_prediction
    
    # Sureshot with enhanced logic
    sureshot = None
    confidence = abs(big_votes - small_votes)
    if final_add_prediction == final_sub_prediction and confidence >= 3:
        sureshot = final_add_prediction
    
    return {
        'target_numbers': target_numbers,
        'add_result': max(5, add_result) if final_add_prediction == 'BIG' else min(4, add_result),
        'sub_result': max(5, sub_result) if final_sub_prediction == 'BIG' else min(4, sub_result),
        'add_prediction': final_add_prediction,
        'sub_prediction': final_sub_prediction,
        'sureshot': sureshot,
        'add_steps': add_steps,
        'diff_steps': diff_steps,
        'numbers': numbers,
        'confidence': confidence,
        'methods': methods
    }

# API functions
async def get_current_period(platform: str) -> Optional[str]:
    """Get current period from API"""
    try:
        config = API_CONFIGS[platform]
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'Accept': 'application/json, text/plain, */*'
        }
        
        if platform == 'mysgame':
            headers['Authorization'] = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
        
        data = {
            'typeId': config['type_id'],
            'language': 0,
            'random': '880a77ad8a254991af1454e9dd0c596b',
            'signature': 'D6537B2B2809B009697080F11A9D2DFF',
            'timestamp': int(datetime.now().timestamp())
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(config['period_api'], headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('data', {}).get('issueNumber'):
                        return result['data']['issueNumber']
    except Exception as e:
        logger.error(f"Error getting current period for {platform}: {e}")
    
    return None

async def get_history_numbers(platform: str) -> Optional[List[int]]:
    """Get historical numbers from API"""
    try:
        config = API_CONFIGS[platform]
        
        if platform == 'mzplay':
            headers = {
                'Content-Type': 'application/json;charset=UTF-8',
                'Accept': 'application/json, text/plain, */*'
            }
            data = {
                'pageSize': 10,
                'pageNo': 1,
                'typeId': config['type_id'],
                'language': 0,
                'random': "963e75bd7c5a4029bc1fb21a8766737f",
                'signature': "3CAB87E6962B657396C21BE732999B25",
                'timestamp': int(datetime.now().timestamp())
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(config['history_api'], headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('data', {}).get('list'):
                            return [int(item['number']) for item in result['data']['list'][:10]]
        
        else:  # mysgame
            url = f"{config['history_api']}?ts={int(datetime.now().timestamp() * 1000)}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('data', {}).get('list'):
                            return [int(item['number']) for item in result['data']['list'][:10]]
                            
    except Exception as e:
        logger.error(f"Error getting history for {platform}: {e}")
    
    return None

async def get_current_result(platform: str) -> Optional[Dict]:
    """Get latest result for verification"""
    numbers = await get_history_numbers(platform)
    if numbers and len(numbers) > 0:
        # This would be from a separate result API in real implementation
        # For now, using the same API
        return {
            'period': 'latest',  # Would get actual period
            'number': numbers[0]
        }
    return None

# Message formatting
def format_message(platform: str, prediction: Dict, period: str, result_data: Dict = None) -> str:
    """Format the prediction message"""
    period_last2 = period[-2:] if len(period) >= 2 else period
    platform_title = 'Mᴢᴘʟᴀʏ Pʀᴇᴅɪᴄᴛɪᴏɴ' if platform == 'mzplay' else 'Mʏsɢᴀᴍᴇ Pʀᴇᴅɪᴄᴛɪᴏɴ'
    mode_display = 'sᴜʀᴇsʜᴏᴛ'
    
    # Update result for previous prediction if available
    if result_data:
        result_symbol = '✅✅' if result_data['is_win'] else '❌❌'
        prev_prediction_char = result_data['prediction'][0]
        bet_multiplier = f"x{result_data['bet_amount']}" if result_data.get('bet_amount', 1) > 1 else ''
        result_line = f"{result_data['period_last2']} {prev_prediction_char}{prev_prediction_char}{bet_multiplier}{result_symbol}{result_data['actual_number']}"
        
        # Update the last line in message history
        if game_settings.message_history[platform]:
            game_settings.message_history[platform][-1] = result_line
    
    # Determine prediction based on mode
    if game_settings.current_mode == 'sureshot':
        if prediction['sureshot']:
            final_prediction = prediction['sureshot']
            # Add current prediction with bet amount
            current_bet_multiplier = f"x{game_settings.bet_amount}" if game_settings.bet_amount > 1 else ''
            current_line = f"{period_last2} {final_prediction[0]}{final_prediction[0]}{current_bet_multiplier}"
            game_settings.message_history[platform].append(current_line)
        else:
            # Handle SKIP with smart grouping
            current_line = f"{period_last2} SKIP"
            
            # Check if last line was also SKIP and group them
            if game_settings.message_history[platform]:
                last_line = game_settings.message_history[platform][-1]
                
                if 'SKIP' in last_line:
                    # Check if it's already a range (contains '-')
                    if '-' in last_line:
                        # Extract the range and update end period
                        parts = last_line.split(' ')
                        range_parts = parts[0].split('-')
                        start_period = range_parts[0]
                        # Update to new range
                        game_settings.message_history[platform][-1] = f"{start_period}-{period_last2} SKIP"
                    else:
                        # Convert single SKIP to range
                        last_period = last_line.split(' ')[0]
                        game_settings.message_history[platform][-1] = f"{last_period}-{period_last2} SKIP"
                else:
                    # Add new SKIP line normally
                    game_settings.message_history[platform].append(current_line)
            else:
                # First line, add normally
                game_settings.message_history[platform].append(current_line)
            
            final_prediction = None  # No prediction to track
    else:
        # Normal mode
        final_prediction = prediction['sub_prediction']
        current_bet_multiplier = f"x{game_settings.bet_amount}" if game_settings.bet_amount > 1 else ''
        current_line = f"{period_last2} {final_prediction[0]}{final_prediction[0]}{current_bet_multiplier}"
        game_settings.message_history[platform].append(current_line)
    
    # Build complete message
    message = f"{platform_title}\nMᴏᴅᴇ : {mode_display}\n\n"
    message += '\n'.join(game_settings.message_history[platform])
    
    # Add stats
    message += f"\n\n{game_settings.wins}Wɪɴs {game_settings.losses}Lᴏsᴇ\n"
    message += f"WɪɴSᴛʀᴇᴀᴋs : {game_settings.longest_win_streak}\n"
    message += f"LᴏsᴇSᴛʀᴇᴀᴋs : {game_settings.longest_loss_streak}\n\n"
    message += f"Rᴇɢɪsᴛᴇʀ :\n{API_CONFIGS[platform]['register_link']}\n\n"
    message += "Bᴏᴛ Bʏ @CKWinGg1330"
    
    return message, final_prediction

def update_game_stats(is_win: bool):
    """Update game statistics"""
    if is_win:
        game_settings.wins += 1
        
        # Update streak logic
        if game_settings.is_win_streak:
            game_settings.current_streak += 1
        else:
            game_settings.is_win_streak = True
            game_settings.current_streak = 1
        
        # Update longest win streak
        if game_settings.current_streak > game_settings.longest_win_streak:
            game_settings.longest_win_streak = game_settings.current_streak
        
        # Reset bet amount on win
        game_settings.bet_amount = game_settings.base_bet_amount
    else:
        game_settings.losses += 1
        
        # Update streak logic
        if not game_settings.is_win_streak:
            game_settings.current_streak += 1
        else:
            game_settings.is_win_streak = False
            game_settings.current_streak = 1
        
        # Update longest loss streak
        if game_settings.current_streak > game_settings.longest_loss_streak:
            game_settings.longest_loss_streak = game_settings.current_streak
        
        # Double bet amount on loss (Martingale system)
        game_settings.bet_amount *= 2
    
    game_settings.current_game += 1

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    global ADMIN_ID
    user = update.effective_user
    
    # Add user to database
    add_user(user.id, user.username, user.first_name, user.last_name)
    
    # Set admin if first time
    if ADMIN_ID is None:
        ADMIN_ID = user.id
    
    # Create inline keyboard with register links
    keyboard = [
        [InlineKeyboardButton("🎯 Register MZPlay", url=API_CONFIGS['mzplay']['register_link'])],
        [InlineKeyboardButton("🚀 Register MysGame", url=API_CONFIGS['mysgame']['register_link'])],
        [InlineKeyboardButton("📊 Bot Status", callback_data="status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = f"""
🤖 **Wingo Prediction Bot**

Welcome {user.first_name}! 

🎯 **Features:**
• Enhanced TeamCK Algorithm
• Sureshot Predictions  
• Smart Bet Management
• Real-time Updates

📈 **Platforms:**
• MZPlay (30s updates)
• MysGame (1m updates)

🎁 **Register now and start winning!**

Bᴏᴛ Bʏ @CKWinGg1330
"""
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin control menu"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use admin commands.")
        return
    
    keyboard = [
        [InlineKeyboardButton("▶️ Start Bot", callback_data="admin_start")],
        [InlineKeyboardButton("⏹️ Stop Bot", callback_data="admin_stop")],
        [InlineKeyboardButton("📊 Bot Status", callback_data="admin_status")],
        [InlineKeyboardButton("🎯 Switch to MZPlay", callback_data="admin_mzplay")],
        [InlineKeyboardButton("🎮 Switch to MysGame", callback_data="admin_mysgame")],
        [InlineKeyboardButton("📈 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("🗑️ Reset Stats", callback_data="admin_reset")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status = "🟢 Running" if game_settings.bot_running else "🔴 Stopped"
    platform = API_CONFIGS[game_settings.current_platform]['name']
    
    message = f"""
🔧 **Admin Control Panel**

**Bot Status:** {status}
**Platform:** {platform}
**Mode:** {game_settings.current_mode}
**Games:** {game_settings.current_game}/{game_settings.total_games}
**Record:** {game_settings.wins}W/{game_settings.losses}L

**Users:** {len(get_all_users())} registered
"""
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "status":
        status = "🟢 Running" if game_settings.bot_running else "🔴 Stopped"
        platform = API_CONFIGS[game_settings.current_platform]['name']
        
        message = f"""
📊 **Bot Status**

**Status:** {status}
**Platform:** {platform}
**Games:** {game_settings.current_game}/{game_settings.total_games}
**Record:** {game_settings.wins}W/{game_settings.losses}L
**Win Rate:** {(game_settings.wins/max(1,game_settings.current_game)*100):.1f}%

**Best Streaks:**
WɪɴSᴛʀᴇᴀᴋs: {game_settings.longest_win_streak}
LᴏsᴇSᴛʀᴇᴀᴋs: {game_settings.longest_loss_streak}
"""
        await query.edit_message_text(message, parse_mode='Markdown')
    
    elif query.data.startswith("admin_") and query.from_user.id == ADMIN_ID:
        await handle_admin_action(query)

async def handle_admin_action(query):
    """Handle admin actions"""
    action = query.data.replace("admin_", "")
    
    if action == "start":
        game_settings.bot_running = True
        await query.edit_message_text("✅ Bot started successfully!")
        # Start the prediction loop
        asyncio.create_task(prediction_loop())
        
    elif action == "stop":
        game_settings.bot_running = False
        await query.edit_message_text("⏹️ Bot stopped successfully!")
        
    elif action == "mzplay":
        game_settings.current_platform = 'mzplay'
        await query.edit_message_text("🎯 Switched to MZPlay platform!")
        
    elif action == "mysgame":
        game_settings.current_platform = 'mysgame'
        await query.edit_message_text("🎮 Switched to MysGame platform!")
        
    elif action == "reset":
        # Reset all stats
        game_settings.current_game = 0
        game_settings.wins = 0
        game_settings.losses = 0
        game_settings.longest_win_streak = 0
        game_settings.longest_loss_streak = 0
        game_settings.current_streak = 0
        game_settings.bet_amount = 1
        game_settings.message_history = {'mzplay': [], 'mysgame': []}
        game_settings.prediction_history = {'mzplay': [], 'mysgame': []}
        await query.edit_message_text("🗑️ Statistics reset successfully!")
        
    elif action == "stats":
        win_rate = (game_settings.wins/max(1,game_settings.current_game)*100)
        message = f"""
📈 **Detailed Statistics**

**Games Played:** {game_settings.current_game}/{game_settings.total_games}
**Wins:** {game_settings.wins}
**Losses:** {game_settings.losses}
**Win Rate:** {win_rate:.1f}%

**Streaks:**
• Longest Win: {game_settings.longest_win_streak}
• Longest Loss: {game_settings.longest_loss_streak}
• Current: {'W' if game_settings.is_win_streak else 'L'}{game_settings.current_streak}

**Betting:**
• Current Bet: x{game_settings.bet_amount}
• Base Bet: x{game_settings.base_bet_amount}

**Users:** {len(get_all_users())} registered
"""
        await query.edit_message_text(message, parse_mode='Markdown')

async def broadcast_message(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send message to all users"""
    users = get_all_users()
    successful = 0
    failed = 0
    
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            successful += 1
            await asyncio.sleep(0.1)  # Rate limiting
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send to {user_id}: {e}")
    
    logger.info(f"Broadcast completed: {successful} successful, {failed} failed")

async def prediction_loop():
    """Main prediction loop"""
    while game_settings.bot_running:
        try:
            platform = game_settings.current_platform
            config = API_CONFIGS[platform]
            
            # Get current period
            current_period = await get_current_period(platform)
            if not current_period:
                logger.error(f"Failed to get current period for {platform}")
                await asyncio.sleep(30)
                continue
            
            # Check if already processed
            if current_period == game_settings.last_processed_period[platform]:
                await asyncio.sleep(config['interval'])
                continue
            
            # Get historical numbers
            numbers = await get_history_numbers(platform)
            if not numbers or len(numbers) < 5:
                logger.error(f"Insufficient history data for {platform}")
                await asyncio.sleep(30)
                continue
            
            # Calculate prediction
            prediction = calculate_prediction(numbers)
            
            # Check previous results
            result_data = None
            if game_settings.prediction_history[platform]:
                last_prediction = game_settings.prediction_history[platform][-1]
                if not last_prediction['result_processed'] and not last_prediction.get('is_skip', False):
                    # Get result and update stats
                    api_result = await get_current_result(platform)
                    if api_result and api_result['period'] == last_prediction['period']:
                        actual_type = 'SMALL' if api_result['number'] <= 4 else 'BIG'
                        is_win = last_prediction['prediction'] == actual_type
                        
                        update_game_stats(is_win)
                        
                        result_data = {
                            'period_last2': last_prediction['period'][-2:],
                            'prediction': last_prediction['prediction'],
                            'actual_number': api_result['number'],
                            'is_win': is_win,
                            'bet_amount': last_prediction.get('bet_amount', 1)
                        }
                        
                        last_prediction['result_processed'] = True
                        last_prediction['actual_number'] = api_result['number']
                        last_prediction['is_win'] = is_win
            
            # Format and send message
            message, final_prediction = format_message(platform, prediction, current_period, result_data)
            
            # Send to channel
            app = Application.builder().token(BOT_TOKEN).build()
            await app.bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode='Markdown')
            
            # Broadcast to all users
            await broadcast_message(app, message)
            
            # Store prediction if not skipped
            if final_prediction:
                game_settings.prediction_history[platform].append({
                    'period': current_period,
                    'prediction': final_prediction,
                    'result_processed': False,
                    'actual_number': None,
                    'is_win': None,
                    'is_skip': False,
                    'bet_amount': game_settings.bet_amount
                })
                
                # Keep only last 5 predictions
                if len(game_settings.prediction_history[platform]) > 5:
                    game_settings.prediction_history[platform] = game_settings.prediction_history[platform][-5:]
            
            # Update last processed period
            game_settings.last_processed_period[platform] = current_period
            
            # Check if game limit reached
            if game_settings.current_game >= game_settings.total_games:
                game_settings.bot_running = False
                await app.bot.send_message(
                    chat_id=ADMIN_ID, 
                    text=f"🎯 Game limit reached! Final: {game_settings.wins}W/{game_settings.losses}L"
                )
            
            # Wait for next interval
            await asyncio.sleep(config['interval'])
            
        except Exception as e:
            logger.error(f"Error in prediction loop: {e}")
            await asyncio.sleep(30)

def main():
    """Main function"""
    # Initialize database
    init_db()
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_menu))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Bot started!")
    
    # Run the bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
