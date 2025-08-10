import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import sqlite3
from datetime import datetime
import os

# 设置日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot配置
BOT_TOKEN = '7838707734:AAHUINQudboDg6C1y8oS1K9hy6koNucyUG4'

# 管理员ID
ADMIN_ID = 7094343615

# 注册链接
MYSGAME_LINK = "https://myslotto.net/#/register?invitationCode=28487236736"
MZPLAY_LINK = "https://mz155.com/#/register?invitationCode=24667538788"
FLEXORY_LINK = "https://t.me/TeamCKGroup/854"

class AgentBot:
    def __init__(self):
        self.init_database()
        self.pending_broadcast = False
        self.broadcast_message = None
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect('agent_bot.db')
        cursor = conn.cursor()
        
        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_date TEXT,
                last_activity TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # 创建统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT,
                user_id INTEGER,
                details TEXT,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("数据库初始化完成")
    
    def add_user(self, user_id, username=None, first_name=None, last_name=None):
        """添加用户到数据库"""
        conn = sqlite3.connect('agent_bot.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, joined_date, last_activity, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            ''', (
                user_id, 
                username, 
                first_name, 
                last_name, 
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            logger.info(f"用户 {user_id} 已添加到数据库")
            return True
        except Exception as e:
            logger.error(f"添加用户失败: {e}")
            return False
        finally:
            conn.close()
    
    def update_user_activity(self, user_id):
        """更新用户活动时间"""
        conn = sqlite3.connect('agent_bot.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users SET last_activity = ? WHERE user_id = ?
            ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
            conn.commit()
        except Exception as e:
            logger.error(f"更新用户活动失败: {e}")
        finally:
            conn.close()
    
    def get_all_users(self):
        """获取所有活跃用户ID"""
        conn = sqlite3.connect('agent_bot.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT user_id FROM users WHERE is_active = 1')
            users = [row[0] for row in cursor.fetchall()]
            return users
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_user_stats(self):
        """获取用户统计"""
        conn = sqlite3.connect('agent_bot.db')
        cursor = conn.cursor()
        
        try:
            # 总用户数
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
            total_users = cursor.fetchone()[0]
            
            # 今日新用户
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(joined_date) = ?', (today,))
            today_new = cursor.fetchone()[0]
            
            # 最近活跃用户（24小时内）
            cursor.execute('''
                SELECT COUNT(*) FROM users 
                WHERE datetime(last_activity) > datetime('now', '-1 day') AND is_active = 1
            ''')
            active_24h = cursor.fetchone()[0]
            
            return {
                'total_users': total_users,
                'today_new': today_new,
                'active_24h': active_24h
            }
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return {'total_users': 0, 'today_new': 0, 'active_24h': 0}
        finally:
            conn.close()
    
    def log_action(self, action_type, user_id, details=None):
        """记录用户行为"""
        conn = sqlite3.connect('agent_bot.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO statistics (action_type, user_id, details, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (action_type, user_id, details, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
        except Exception as e:
            logger.error(f"记录行为失败: {e}")
        finally:
            conn.close()

# 初始化Bot
agent_bot = AgentBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """启动命令"""
    user = update.effective_user
    user_id = user.id
    
    # 添加用户到数据库
    agent_bot.add_user(
        user_id=user_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # 记录启动行为
    agent_bot.log_action('start', user_id)
    
    # 欢迎消息
    welcome_text = f"""🎉 欢迎使用 TeamCK Agent Bot！

👋 你好 {user.first_name or 'Friend'}！

🎯 **可用功能**:
🔹 注册推荐平台
🔹 购买专业预测
🔹 获取最新资讯

💰 **赚钱机会**: 通过我们的推荐链接注册，获得丰厚奖励！

🎲 **精准预测**: 专业团队提供高准确率预测服务！

📱 选择下方功能开始体验："""
    
    keyboard = [
        [InlineKeyboardButton("🎰 注册游戏平台", callback_data='register_platforms')],
        [InlineKeyboardButton("🎯 购买预测服务", callback_data='buy_predictions')],
        [InlineKeyboardButton("📊 我的信息", callback_data='my_info')],
        [InlineKeyboardButton("ℹ️ 帮助中心", callback_data='help_center')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理按钮回调"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    agent_bot.update_user_activity(user_id)
    
    if query.data == 'register_platforms':
        agent_bot.log_action('view_platforms', user_id)
        
        platform_text = """🎰 注册游戏平台

💎 **推荐优质平台**:

🎲 **MySGame** - 信誉第一
• 安全可靠的游戏平台
• 丰富的游戏选择
• 快速提现服务
• 24/7客服支持

🎯 **MzPlay** - 奖励丰厚  
• 高赔率游戏
• 新手奖励优厚
• 每日签到奖励
• VIP专属福利

🔥 **注册优势**:
✅ 通过专属链接注册获得额外奖励
✅ 专业客服一对一服务
✅ 独家优惠活动参与权
✅ 安全资金保障

💰 **奖励说明**:
• 首次注册: 额外奖金
• 首次充值: 充值奖励
• 推荐好友: 推荐佣金

⚠️ **注意事项**:
• 请理性游戏，量力而行
• 严禁未成年人参与
• 如有问题请及时联系客服

👇 点击下方按钮选择平台注册："""
        
        platform_keyboard = [
            [InlineKeyboardButton("🎲 注册 MySGame", url=MYSGAME_LINK)],
            [InlineKeyboardButton("🎯 注册 MzPlay", url=MZPLAY_LINK)],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data='main_menu')]
        ]
        platform_markup = InlineKeyboardMarkup(platform_keyboard)
        
        await query.edit_message_text(platform_text, reply_markup=platform_markup)
    
    elif query.data == 'buy_predictions':
        agent_bot.log_action('view_predictions', user_id)
        
        prediction_text = """🎯 Flexory 专业预测服务

🧠 **TeamCK 专业预测团队**:

💎 **服务特色**:
🔹 专业算法分析
🔹 实时数据追踪  
🔹 多策略组合预测
🔹 历史准确率验证
🔹 24小时技术支持

📊 **预测范围**:
• Big/Small 预测
• 数字趋势分析
• 概率计算服务
• 风险评估建议

🏆 **团队优势**:
✅ 多年预测经验
✅ 专业技术团队
✅ 实时数据分析
✅ 客户成功案例众多

💰 **定价方案**:
• 基础版: 日常预测服务
• 专业版: 深度分析+策略
• VIP版: 一对一指导服务

⚠️ **风险提示**:
• 预测仅供参考，不保证100%准确
• 投注有风险，请理性参与
• 建议合理分配资金

🛒 **购买方式**:
点击下方链接查看详细价格和购买方式"""
        
        prediction_keyboard = [
            [InlineKeyboardButton("🛒 查看价格 & 购买", url=FLEXORY_LINK)],
            [InlineKeyboardButton("📱 联系客服", url="https://t.me/TeamCKGroup")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data='main_menu')]
        ]
        prediction_markup = InlineKeyboardMarkup(prediction_keyboard)
        
        await query.edit_message_text(prediction_text, reply_markup=prediction_markup)
    
    elif query.data == 'my_info':
        user = query.from_user
        join_date = datetime.now().strftime('%Y-%m-%d')
        
        info_text = f"""📊 我的信息

👤 **用户资料**:
━━━━━━━━━━━━━━━━━━━━━━━━
🆔 **用户ID**: {user.id}
👤 **姓名**: {user.first_name or 'N/A'} {user.last_name or ''}
📱 **用户名**: @{user.username or 'N/A'}
📅 **加入日期**: {join_date}
🟢 **状态**: 活跃用户

🎯 **使用记录**:
━━━━━━━━━━━━━━━━━━━━━━━━
✅ 已使用启动功能
📱 最后活动: 刚刚
🎲 可使用所有注册链接
🎯 可购买预测服务

💡 **推荐奖励**:
━━━━━━━━━━━━━━━━━━━━━━━━
🎁 分享注册链接给朋友可获得奖励
💰 成功推荐可获得佣金分成
🏆 VIP用户享受专属优惠

📞 **联系方式**:
━━━━━━━━━━━━━━━━━━━━━━━━
🔹 有问题可联系 @TeamCKGroup
🔹 技术支持: @CKWinGg1330
🔹 客服时间: 24/7 在线"""
        
        info_keyboard = [
            [InlineKeyboardButton("🎰 注册平台", callback_data='register_platforms')],
            [InlineKeyboardButton("🎯 购买预测", callback_data='buy_predictions')],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data='main_menu')]
        ]
        info_markup = InlineKeyboardMarkup(info_keyboard)
        
        await query.edit_message_text(info_text, reply_markup=info_markup)
    
    elif query.data == 'help_center':
        help_text = """ℹ️ 帮助中心

❓ **常见问题**:

🎰 **平台注册相关**:
━━━━━━━━━━━━━━━━━━━━━━━━
Q: 注册链接安全吗？
A: 完全安全，这些都是官方推荐链接

Q: 注册后有什么优势？  
A: 通过我们链接注册可获得额外奖励

Q: 忘记密码怎么办？
A: 直接联系平台客服或我们协助处理

🎯 **预测服务相关**:
━━━━━━━━━━━━━━━━━━━━━━━━
Q: 预测准确率如何？
A: 我们团队有丰富经验，但无法保证100%

Q: 如何购买预测服务？
A: 点击购买链接查看详细价格方案

Q: 预测失败怎么办？
A: 我们提供风险控制建议，投注需谨慎

💰 **费用相关**:
━━━━━━━━━━━━━━━━━━━━━━━━
Q: 使用Bot收费吗？
A: Bot使用完全免费

Q: 注册平台收费吗？
A: 注册免费，充值投注另算

Q: 预测服务价格？
A: 点击购买链接查看详细价格

📞 **联系我们**:
━━━━━━━━━━━━━━━━━━━━━━━━
🔹 主群: @TeamCKGroup
🔹 客服: @CKWinGg1330
🔹 技术: 24/7 在线支持

⚠️ **重要提醒**:
• 投注有风险，请理性参与
• 未成年人严禁参与
• 如有争议，以平台规则为准"""
        
        help_keyboard = [
            [InlineKeyboardButton("📱 联系客服", url="https://t.me/TeamCKGroup")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data='main_menu')]
        ]
        help_markup = InlineKeyboardMarkup(help_keyboard)
        
        await query.edit_message_text(help_text, reply_markup=help_markup)
    
    elif query.data == 'main_menu':
        await start(update, context)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员面板"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ 您没有管理员权限")
        return
    
    stats = agent_bot.get_user_stats()
    
    admin_text = f"""🔧 管理员控制面板

📊 **用户统计**:
━━━━━━━━━━━━━━━━━━━━━━━━
👥 总用户数: {stats['total_users']}
🆕 今日新增: {stats['today_new']}
🟢 24h活跃: {stats['active_24h']}

📱 **可用功能**:
━━━━━━━━━━━━━━━━━━━━━━━━
🔹 /send - 群发消息
🔹 /stats - 详细统计
🔹 /users - 用户列表
🔹 /admin - 管理面板

💡 **群发使用方法**:
1. 发送 /send
2. 等待确认提示
3. 发送要群发的消息
4. 系统自动发送给所有用户

⏰ 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    
    admin_keyboard = [
        [InlineKeyboardButton("📊 详细统计", callback_data='admin_stats')],
        [InlineKeyboardButton("👥 用户管理", callback_data='admin_users')],
        [InlineKeyboardButton("📢 群发消息", callback_data='admin_broadcast')]
    ]
    admin_markup = InlineKeyboardMarkup(admin_keyboard)
    
    await update.message.reply_text(admin_text, reply_markup=admin_markup)

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始群发消息"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ 您没有管理员权限")
        return
    
    agent_bot.pending_broadcast = True
    
    await update.message.reply_text(
        "📢 群发模式已启动\n\n"
        "💡 **使用说明**:\n"
        "• 现在发送任何消息都会群发给所有用户\n"
        "• 支持文字、图片、链接等\n"
        "• 发送 /cancel 取消群发\n\n"
        "✏️ 请输入要群发的消息:"
    )

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取消群发"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    agent_bot.pending_broadcast = False
    await update.message.reply_text("❌ 群发已取消")

async def get_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """获取详细统计"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ 您没有管理员权限")
        return
    
    stats = agent_bot.get_user_stats()
    all_users = agent_bot.get_all_users()
    
    stats_text = f"""📊 详细用户统计

📈 **总体数据**:
━━━━━━━━━━━━━━━━━━━━━━━━
👥 总注册用户: {stats['total_users']}
🆕 今日新增用户: {stats['today_new']}
🟢 24小时活跃: {stats['active_24h']}
📱 可群发用户: {len(all_users)}

📅 **时间分析**:
━━━━━━━━━━━━━━━━━━━━━━━━
📊 用户增长稳定
🎯 活跃度良好
💫 参与度较高

🎯 **使用建议**:
━━━━━━━━━━━━━━━━━━━━━━━━
• 定期群发活动信息
• 关注用户活跃度变化  
• 优化推广策略
• 提升用户体验

⏰ 统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    
    await update.message.reply_text(stats_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理普通消息"""
    user_id = update.effective_user.id
    
    # 更新用户活动
    agent_bot.update_user_activity(user_id)
    
    # 检查是否是管理员的群发消息
    if user_id == ADMIN_ID and agent_bot.pending_broadcast:
        await process_broadcast(update, context)
        return
    
    # 普通用户消息处理
    await update.message.reply_text(
        "👋 你好！请使用 /start 查看可用功能\n\n"
        "🎯 **快速导航**:\n"
        "• 🎰 注册游戏平台\n"
        "• 🎯 购买预测服务\n"
        "• 📊 查看个人信息\n"
        "• ℹ️ 获取帮助\n\n"
        "💡 发送 /start 开始使用！"
    )

async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理群发消息"""
    message_text = update.message.text
    all_users = agent_bot.get_all_users()
    
    if not all_users:
        await update.message.reply_text("📊 没有可群发的用户")
        agent_bot.pending_broadcast = False
        return
    
    # 确认群发
    confirm_text = f"""📢 群发确认

📝 **消息内容预览**:
━━━━━━━━━━━━━━━━━━━━━━━━
{message_text}
━━━━━━━━━━━━━━━━━━━━━━━━

👥 **发送对象**: {len(all_users)} 位用户
⏰ **发送时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ **确认发送吗？**"""
    
    confirm_keyboard = [
        [InlineKeyboardButton("✅ 确认发送", callback_data=f'confirm_broadcast_{len(all_users)}')],
        [InlineKeyboardButton("❌ 取消发送", callback_data='cancel_broadcast')]
    ]
    confirm_markup = InlineKeyboardMarkup(confirm_keyboard)
    
    agent_bot.broadcast_message = message_text
    
    await update.message.reply_text(confirm_text, reply_markup=confirm_markup)

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员按钮回调"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("❌ 您没有管理员权限")
        return
    
    if query.data.startswith('confirm_broadcast_'):
        user_count = int(query.data.split('_')[-1])
        await execute_broadcast(query, context, user_count)
        
    elif query.data == 'cancel_broadcast':
        agent_bot.pending_broadcast = False
        agent_bot.broadcast_message = None
        await query.edit_message_text("❌ 群发已取消")
        
    elif query.data == 'admin_stats':
        stats = agent_bot.get_user_stats()
        await query.edit_message_text(
            f"📊 实时统计数据\n\n"
            f"👥 总用户: {stats['total_users']}\n"
            f"🆕 今日新增: {stats['today_new']}\n"
            f"🟢 24h活跃: {stats['active_24h']}\n\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )

async def execute_broadcast(query, context, user_count):
    """执行群发"""
    if not agent_bot.broadcast_message:
        await query.edit_message_text("❌ 消息内容丢失，请重新发送")
        return
    
    await query.edit_message_text(f"📤 开始群发给 {user_count} 位用户...")
    
    all_users = agent_bot.get_all_users()
    success_count = 0
    failed_count = 0
    
    broadcast_text = f"""📢 【TeamCK 官方通知】

{agent_bot.broadcast_message}

━━━━━━━━━━━━━━━━━━━━━━━━
🤖 由 TeamCK Agent Bot 自动发送
📱 如需帮助请联系: @TeamCKGroup"""
    
    for user_id in all_users:
        try:
            await context.bot.send_message(chat_id=user_id, text=broadcast_text)
            success_count += 1
            await asyncio.sleep(0.1)  # 防止发送过快
        except Exception as e:
            failed_count += 1
            logger.error(f"发送给用户 {user_id} 失败: {e}")
    
    # 发送结果报告
    result_text = f"""✅ 群发完成！

📊 **发送结果**:
━━━━━━━━━━━━━━━━━━━━━━━━
✅ 成功发送: {success_count} 用户
❌ 发送失败: {failed_count} 用户
📱 总计用户: {len(all_users)} 用户

⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 失败原因可能：用户屏蔽了bot或删除了对话"""
    
    await context.bot.send_message(chat_id=ADMIN_ID, text=result_text)
    
    # 重置状态
    agent_bot.pending_broadcast = False
    agent_bot.broadcast_message = None
    
    # 记录群发行为
    agent_bot.log_action('broadcast', ADMIN_ID, f'发送给{success_count}用户')

def main():
    """主函数"""
    if not BOT_TOKEN:
        print("❌ 请设置正确的 BOT_TOKEN")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 添加处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("send", send_broadcast))
    application.add_handler(CommandHandler("cancel", cancel_broadcast))
    application.add_handler(CommandHandler("stats", get_user_stats))
    
    # 回调处理器
    application.add_handler(CallbackQueryHandler(button_callback, pattern='^(?!confirm_broadcast_|cancel_broadcast|admin_).*'))
    application.add_handler(CallbackQueryHandler(admin_callback, pattern='^(confirm_broadcast_|cancel_broadcast|admin_).*'))
    
    # 消息处理器
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 TeamCK Agent Bot 启动中...")
    print(f"🔧 管理员ID: {ADMIN_ID}")
    print("🎰 MySGame 注册链接已配置")
    print("🎯 MzPlay 注册链接已配置") 
    print("💎 Flexory 预测服务已配置")
    print("📢 群发功能已启用")
    print("💾 数据库已初始化")
    print("✅ Bot 启动成功！")
    print("\n📝 管理员命令:")
    print("  /admin - 管理面板")
    print("  /send - 群发消息")
    print("  /stats - 查看统计")
    print("  /cancel - 取消群发")
    
    application.run_polling()

if __name__ == '__main__':
    main()
