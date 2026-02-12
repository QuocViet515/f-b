import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.request import HTTPXRequest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
OPHIM_API_BASE = "https://ophim1.com/v1/api"
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
PROXY_URL = os.getenv('PROXY_URL', None)  # Optional proxy

class MovieBot:
    def __init__(self):
        # Tạo request với timeout dài hơn và proxy (nếu có)
        request = HTTPXRequest(
            connection_pool_size=10,
            connect_timeout=30.0,  # 30 giây cho kết nối
            read_timeout=30.0,      # 30 giây cho đọc dữ liệu
            write_timeout=30.0,     # 30 giây cho ghi dữ liệu
            pool_timeout=30.0,      # 30 giây cho pool
            proxy=PROXY_URL         # Sử dụng proxy nếu có
        )
        
        # Xây dựng application với request tùy chỉnh
        self.app = Application.builder().token(BOT_TOKEN).request(request).build()
        
        # Danh sách các danh mục phổ biến
        self.categories = {
            '🎬 Phim mới': 'phim-moi-cap-nhat',
            '🎭 Phim lẻ': 'phim-le',
            '📺 Phim bộ': 'phim-bo',
            '🎉 Hoạt hình': 'hoat-hinh',
            '🎬 Phim viện tưởng': 'phim-vien-tuong',
            '🍿 TV Shows': 'tv-shows'
        }
        self.setup_handlers()
    
    def setup_handlers(self):
        """Thiết lập các handler cho bot"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("danhmuc", self.category_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.search_movie))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /start"""
        welcome_text = """
🎬 *Chào mừng đến với Bot Tìm Phim!*

Tôi có thể giúp bạn tìm kiếm thông tin về các bộ phim.

📝 *Cách sử dụng:*
- Gửi tên phim bạn muốn tìm
- Bot sẽ tìm kiếm và hiển thị kết quả
- Bấm vào các nút để xem chi tiết hoặc link phim

💡 *Lệnh:*
/start - Bắt đầu
/help - Hướng dẫn sử dụng
/danhmuc - Xem danh mục phim

Hãy gửi tên phim để bắt đầu tìm kiếm! 🍿
"""
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /help"""
        help_text = """
📖 *Hướng dẫn sử dụng Bot Tìm Phim*

1️⃣ *Tìm kiếm phim:*
   - Gửi tên phim bạn muốn tìm
   - Ví dụ: "Avengers", "Doraemon", "Bố Già"

2️⃣ *Xem kết quả:*
   - Bot sẽ hiển thị danh sách phim tìm được
   - Bấm "Xem chi tiết" để xem thông tin đầy đủ
   - Bấm "Link phim" để lấy đường dẫn xem phim

3️⃣ *Duyệt phim theo danh mục:*
   - Dùng /danhmuc để xem các danh mục phổ biến
   - Chọn danh mục muốn xem

💡 Bot sử dụng API tìm kiếm chính thức từ Ophim.
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def category_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /danhmuc"""
        category_text = "🎬 *Danh mục phim:*\n\n"
        category_text += "Chọn danh mục bạn muốn xem:\n"
        
        # Tạo inline keyboard cho các danh mục
        keyboard = []
        for name, slug in self.categories.items():
            keyboard.append([InlineKeyboardButton(name, callback_data=f"cat_{slug}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            category_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    def search_movies_api(self, keyword):
        """Tìm kiếm phim qua API"""
        try:
            # Sử dụng API tìm kiếm chính thức
            url = f"{OPHIM_API_BASE}/tim-kiem"
            params = {
                'keyword': keyword
            }
            headers = {"accept": "application/json"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Kiểm tra status và lấy danh sách phim
                if data.get('status') == 'success' and 'data' in data:
                    items = data['data'].get('items', [])
                    
                    if items:
                        return items
                    else:
                        # Nếu không tìm thấy, thử tìm kiếm theo slug
                        return self.search_by_slug(keyword)
            
            return []
        except Exception as e:
            print(f"Error searching movies: {e}")
            return []
    
    def get_movies_by_category(self, slug, page=1):
        """Lấy danh sách phim theo bộ lọc (thể loại, quốc gia, etc.)"""
        try:
            # API lấy danh sách theo slug
            url = f"{OPHIM_API_BASE}/danh-sach/{slug}"
            params = {'page': page}
            headers = {"accept": "application/json"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success' and 'data' in data:
                    return data['data'].get('items', [])
            
            return []
        except Exception as e:
            print(f"Error getting movies by category: {e}")
            return []
    
    def search_by_slug(self, keyword):
        """Tìm kiếm phim bằng slug"""
        try:
            # Chuyển keyword thành slug format (lowercase, replace space with -)
            slug = keyword.lower().replace(' ', '-')
            url = f"{OPHIM_API_BASE}/phim/{slug}"
            headers = {"accept": "application/json"}
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and 'data' in data:
                    item = data['data'].get('item')
                    if item:
                        return [item]
            
            return []
        except Exception as e:
            print(f"Error searching by slug: {e}")
            return []
    
    def get_movie_details(self, slug):
        """Lấy chi tiết phim theo slug"""
        try:
            url = f"{OPHIM_API_BASE}/phim/{slug}"
            headers = {"accept": "application/json"}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and 'data' in data:
                    return data['data'].get('item')
            elif response.status_code == 404:
                print(f"Movie not found: {slug}")
            
            return None
        except Exception as e:
            print(f"Error getting movie details: {e}")
            return None
    
    def format_movie_info(self, movie, show_full=False):
        """Format thông tin phim"""
        name = movie.get('name', 'N/A')
        origin_name = movie.get('origin_name', 'N/A')
        year = movie.get('year', 'N/A')
        quality = movie.get('quality', 'N/A')
        lang = movie.get('lang', 'N/A')
        
        text = f"🎬 *{name}*\n"
        text += f"📝 Tên gốc: {origin_name}\n"
        text += f"📅 Năm: {year}\n"
        text += f"🎞️ Chất lượng: {quality} | Ngôn ngữ: {lang}\n"
        
        if show_full:
            # Thêm thông tin chi tiết
            category = movie.get('category', {})
            if isinstance(category, list):
                categories = ', '.join([c.get('name', '') for c in category])
                text += f"🎭 Thể loại: {categories}\n"
            
            country = movie.get('country', [])
            if isinstance(country, list) and country:
                countries = ', '.join([c.get('name', '') for c in country])
                text += f"🌍 Quốc gia: {countries}\n"
            
            time = movie.get('time', 'N/A')
            text += f"⏱️ Thời lượng: {time}\n"
            
            episode_current = movie.get('episode_current', 'N/A')
            episode_total = movie.get('episode_total', 'N/A')
            text += f"📺 Tập: {episode_current}/{episode_total}\n"
            
            # Thêm thông tin đạo diễn và diễn viên
            director = movie.get('director', [])
            if isinstance(director, list) and director:
                directors = ', '.join(director[:3])  # Giới hạn 3 đạo diễn
                text += f"🎬 Đạo diễn: {directors}\n"
            
            actor = movie.get('actor', [])
            if isinstance(actor, list) and actor:
                actors = ', '.join(actor[:5])  # Giới hạn 5 diễn viên
                text += f"🎭 Diễn viên: {actors}\n"
            
            # Thêm rating IMDB/TMDB
            imdb = movie.get('imdb', {})
            if isinstance(imdb, dict) and imdb.get('id'):
                vote_avg = imdb.get('vote_average', 0)
                vote_count = imdb.get('vote_count', 0)
                if vote_avg:
                    text += f"⭐ IMDB: {vote_avg}/10 ({vote_count:,} votes)\n"
            
            tmdb = movie.get('tmdb', {})
            if isinstance(tmdb, dict) and tmdb.get('id') and not imdb.get('id'):
                vote_avg = tmdb.get('vote_average', 0)
                if vote_avg:
                    text += f"⭐ TMDB: {vote_avg}/10\n"
            
            # Lượt xem
            view = movie.get('view', 0)
            if view:
                text += f"👁️ Lượt xem: {view:,}\n"
            
            content = movie.get('content', '')
            if content:
                # Giới hạn độ dài nội dung
                short_content = content[:300] + "..." if len(content) > 300 else content
                text += f"\n📖 Nội dung:\n{short_content}\n"
        
        return text
    
    def get_movie_links(self, movie):
        """Lấy các link liên quan đến phim (thông tin cơ bản)"""
        links = []
        
        # Link chi tiết phim trên Ophim
        slug = movie.get('slug', '')
        if slug:
            ophim_link = f"https://ophim1.com/phim/{slug}"
            links.append(('Xem trên Ophim', ophim_link))
        
        # Link poster
        poster_url = movie.get('poster_url', '')
        if poster_url:
            links.append(('Poster phim', poster_url))
        
        # Link trailer (nếu có)
        trailer_url = movie.get('trailer_url', '')
        if trailer_url:
            links.append(('Trailer', trailer_url))
        
        return links
    
    def get_all_episode_links(self, movie):
        """Lấy tất cả link video từ tất cả server và tập phim"""
        episodes = movie.get('episodes', [])
        servers_data = []
        
        for server in episodes:
            server_name = server.get('server_name', 'Server')
            server_items = server.get('server_data', [])
            
            episodes_list = []
            for ep in server_items:
                ep_name = ep.get('name', 'Tập ?')
                link_m3u8 = ep.get('link_m3u8', '')
                link_embed = ep.get('link_embed', '')
                
                if link_m3u8 or link_embed:
                    episodes_list.append({
                        'name': ep_name,
                        'link_m3u8': link_m3u8,
                        'link_embed': link_embed
                    })
            
            if episodes_list:
                servers_data.append({
                    'server_name': server_name,
                    'episodes': episodes_list
                })
        
        return servers_data
    
    def format_episode_links_text(self, movie, server_index=0):
        """Format text hiển thị link video của một server"""
        servers = self.get_all_episode_links(movie)
        
        if not servers:
            return None, None
        
        if server_index >= len(servers):
            server_index = 0
        
        server = servers[server_index]
        server_name = server['server_name']
        episodes = server['episodes']
        
        text = f"🎬 *{movie.get('name')}*\n"
        text += f"📡 Server: *{server_name}*\n"
        text += f"📺 Có {len(episodes)} tập\n\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Hiển thị tối đa 10 tập đầu tiên
        display_episodes = episodes[:10]
        
        for idx, ep in enumerate(display_episodes, 1):
            ep_name = ep['name']
            text += f"*{idx}. {ep_name}*\n"
            
            if ep['link_m3u8']:
                text += f"   🎥 [Stream M3U8]({ep['link_m3u8']})\n"
            
            if ep['link_embed']:
                text += f"   🎬 [Player Embed]({ep['link_embed']})\n"
            
            text += "\n"
        
        if len(episodes) > 10:
            text += f"\n_... và {len(episodes) - 10} tập khác_\n"
        
        text += "\n💡 *Hướng dẫn:*\n"
        text += "▸ *Stream M3U8*: Link video trực tiếp (HLS)\n"
        text += "▸ *Player Embed*: Trang player đầy đủ\n"
        
        return text, len(servers)
    
    async def search_movie(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý tìm kiếm phim"""
        keyword = update.message.text.strip()
        
        if not keyword:
            await update.message.reply_text("Vui lòng nhập tên phim bạn muốn tìm!")
            return
        
        # Gửi message đang tìm kiếm
        processing_msg = await update.message.reply_text(f"🔍 Đang tìm kiếm phim '{keyword}'...")
        
        # Tìm kiếm phim
        movies = self.search_movies_api(keyword)
        
        if not movies:
            await processing_msg.edit_text(
                f"❌ Không tìm thấy phim nào với từ khóa '{keyword}'.\n\n"
                "💡 Hãy thử:\n"
                "- Kiểm tra lại chính tả\n"
                "- Sử dụng tên tiếng Anh hoặc tên gốc\n"
                "- Tìm kiếm với từ khóa ngắn gọn hơn"
            )
            return
        
        # Hiển thị kết quả
        result_text = f"🎬 *Tìm thấy {len(movies)} kết quả cho '{keyword}':*\n\n"
        
        for idx, movie in enumerate(movies[:5], 1):  # Giới hạn 5 kết quả
            result_text += f"{idx}. {self.format_movie_info(movie)}\n"
            result_text += "─" * 30 + "\n\n"
        
        # Tạo inline keyboard cho từng phim
        keyboard = []
        for idx, movie in enumerate(movies[:5]):
            slug = movie.get('slug', '')
            name = movie.get('name', f'Phim {idx+1}')
            # Giới hạn độ dài tên button
            button_name = name[:30] + "..." if len(name) > 30 else name
            
            keyboard.append([
                InlineKeyboardButton(f"📖 {button_name}", callback_data=f"detail_{slug}"),
                InlineKeyboardButton("🔗 Link phim", callback_data=f"links_{slug}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_msg.edit_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý callback từ inline buttons"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if callback_data.startswith('detail_'):
            # Hiển thị chi tiết phim
            slug = callback_data.replace('detail_', '')
            movie = self.get_movie_details(slug)
            
            if movie:
                detail_text = self.format_movie_info(movie, show_full=True)
                
                # Tạo keyboard với link
                keyboard = [[
                    InlineKeyboardButton("🔗 Lấy link phim", callback_data=f"links_{slug}"),
                    InlineKeyboardButton("🔙 Quay lại", callback_data="back")
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Gửi ảnh poster nếu có
                poster_url = movie.get('poster_url', '') or movie.get('thumb_url', '')
                
                try:
                    if poster_url:
                        await query.message.reply_photo(
                            photo=poster_url,
                            caption=detail_text,
                            parse_mode='Markdown',
                            reply_markup=reply_markup
                        )
                    else:
                        await query.message.reply_text(
                            detail_text,
                            parse_mode='Markdown',
                            reply_markup=reply_markup
                        )
                except Exception as e:
                    # Nếu không gửi được ảnh, chỉ gửi text
                    await query.message.reply_text(
                        detail_text,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
            else:
                await query.message.reply_text("❌ Không thể lấy thông tin chi tiết phim!")
        
        elif callback_data.startswith('links_'):
            # Hiển thị các link liên quan
            slug = callback_data.replace('links_', '')
            movie = self.get_movie_details(slug)
            
            if movie:
                # Hiển thị menu chọn: Link cơ bản hoặc Link video
                movie_name = movie.get('name', 'Phim')
                
                keyboard = []
                
                # Nút xem link video
                servers = self.get_all_episode_links(movie)
                if servers:
                    keyboard.append([InlineKeyboardButton("🎬 Xem Link Video", callback_data=f"videos_{slug}_0")])
                
                # Nút xem link khác (poster, trailer, etc)
                basic_links = self.get_movie_links(movie)
                if basic_links:
                    keyboard.append([InlineKeyboardButton("🔗 Link khác (Poster, Trailer)", callback_data=f"basic_{slug}")])
                
                keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data="back")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                menu_text = f"🔗 *Link cho phim: {movie_name}*\n\n"
                menu_text += "Chọn loại link bạn muốn xem:"
                
                await query.message.reply_text(
                    menu_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await query.message.reply_text("❌ Không thể lấy thông tin phim!")
        
        elif callback_data.startswith('videos_'):
            # Hiển thị link video theo server
            parts = callback_data.replace('videos_', '').split('_')
            slug = '_'.join(parts[:-1])
            server_index = int(parts[-1])
            
            movie = self.get_movie_details(slug)
            
            if movie:
                links_text, total_servers = self.format_episode_links_text(movie, server_index)
                
                if links_text:
                    # Tạo keyboard cho chuyển server
                    keyboard = []
                    
                    # Nút chuyển server nếu có nhiều hơn 1 server
                    if total_servers > 1:
                        server_buttons = []
                        for i in range(total_servers):
                            if i == server_index:
                                server_buttons.append(InlineKeyboardButton(f"• S{i+1} •", callback_data=f"videos_{slug}_{i}"))
                            else:
                                server_buttons.append(InlineKeyboardButton(f"S{i+1}", callback_data=f"videos_{slug}_{i}"))
                        
                        # Chia buttons thành hàng (tối đa 4 buttons/hàng)
                        for i in range(0, len(server_buttons), 4):
                            keyboard.append(server_buttons[i:i+4])
                    
                    keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data=f"links_{slug}")])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.message.reply_text(
                        links_text,
                        parse_mode='Markdown',
                        reply_markup=reply_markup,
                        disable_web_page_preview=True
                    )
                else:
                    await query.message.reply_text("❌ Không tìm thấy link video nào cho phim này!")
            else:
                await query.message.reply_text("❌ Không thể lấy thông tin phim!")
        
        elif callback_data.startswith('basic_'):
            # Hiển thị các link cơ bản (poster, trailer, etc)
            slug = callback_data.replace('basic_', '')
            movie = self.get_movie_details(slug)
            
            if movie:
                links = self.get_movie_links(movie)
                
                if links:
                    links_text = f"🔗 *Link khác cho phim: {movie.get('name')}*\n\n"
                    
                    for link_name, link_url in links:
                        links_text += f"▸ [{link_name}]({link_url})\n"
                    
                    keyboard = [[
                        InlineKeyboardButton("🔙 Quay lại", callback_data=f"links_{slug}")
                    ]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.message.reply_text(
                        links_text,
                        parse_mode='Markdown',
                        reply_markup=reply_markup,
                        disable_web_page_preview=False
                    )
                else:
                    await query.message.reply_text("❌ Không tìm thấy link nào!")
            else:
                await query.message.reply_text("❌ Không thể lấy thông tin phim!")
        
        elif callback_data.startswith('cat_'):
            # Hiển thị phim theo danh mục
            slug = callback_data.replace('cat_', '')
            
            # Tìm tên danh mục
            category_name = "Danh mục"
            for name, cat_slug in self.categories.items():
                if cat_slug == slug:
                    category_name = name
                    break
            
            await query.message.reply_text(f"🔍 Đang tải {category_name}...")
            
            movies = self.get_movies_by_category(slug)
            
            if not movies:
                await query.message.reply_text(
                    f"❌ Không thể tải phim từ danh mục '{category_name}'.\n\n"
                    "Vui lòng thử lại sau!"
                )
                return
            
            # Hiển thị kết quả
            result_text = f"🎬 *{category_name}*\n\n"
            result_text += f"📋 Hiển thị {min(len(movies), 5)} phim:\n\n"
            
            for idx, movie in enumerate(movies[:5], 1):
                result_text += f"{idx}. {self.format_movie_info(movie)}\n"
                result_text += "─" * 30 + "\n\n"
            
            # Tạo inline keyboard
            keyboard = []
            for idx, movie in enumerate(movies[:5]):
                slug_movie = movie.get('slug', '')
                name = movie.get('name', f'Phim {idx+1}')
                button_name = name[:30] + "..." if len(name) > 30 else name
                
                keyboard.append([
                    InlineKeyboardButton(f"📖 {button_name}", callback_data=f"detail_{slug_movie}"),
                    InlineKeyboardButton("🔗 Link phim", callback_data=f"links_{slug_movie}")
                ])
            
            # Thêm nút quay lại danh mục
            keyboard.append([InlineKeyboardButton("🔙 Quay lại danh mục", callback_data="back_to_cat")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                result_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
        elif callback_data == 'back_to_cat':
            # Quay lại menu danh mục
            category_text = "🎬 *Danh mục phim:*\n\n"
            category_text += "Chọn danh mục bạn muốn xem:\n"
            
            keyboard = []
            for name, slug in self.categories.items():
                keyboard.append([InlineKeyboardButton(name, callback_data=f"cat_{slug}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                category_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
        elif callback_data == 'back':
            await query.message.reply_text("Gửi tên phim để tiếp tục tìm kiếm! 🔍")
    
    def run(self):
        """Chạy bot"""
        print("🤖 Bot đang khởi động...")
        if PROXY_URL:
            print(f"🌐 Sử dụng proxy: {PROXY_URL}")
        print(f"⏱️  Timeout: 30 giây (tăng để tránh lỗi connection)")
        print(f"🚀 Bot đã sẵn sàng! Bắt đầu polling...")
        self.app.run_polling()

def main():
    if not BOT_TOKEN:
        print("❌ Lỗi: Không tìm thấy TELEGRAM_BOT_TOKEN!")
        print("Vui lòng tạo file .env và thêm token của bot")
        print("\nXem hướng dẫn trong file TROUBLESHOOTING.md")
        return
    
    try:
        print("="*60)
        print("🎬 BOT TÌM KIẾM PHIM TELEGRAM")
        print("="*60)
        bot = MovieBot()
        bot.run()
    except Exception as e:
        error_name = type(e).__name__
        print("\n" + "="*60)
        print(f"❌ LỖI: {error_name}")
        print("="*60)
        print(f"Chi tiết: {str(e)}\n")
        
        if "TimedOut" in error_name or "ConnectTimeout" in error_name:
            print("🔍 NGUYÊN NHÂN: Không kết nối được Telegram API")
            print("\n✅ GIẢI PHÁP:")
            print("1. Bật VPN (khuyên dùng nhất)")
            print("2. Cấu hình proxy trong file .env:")
            print("   PROXY_URL=http://127.0.0.1:7890")
            print("3. Kiểm tra kết nối internet")
            print("\n📖 Xem hướng dẫn chi tiết: TROUBLESHOOTING.md")
            print("   Hoặc: https://github.com/yourusername/tele_bot/blob/main/TROUBLESHOOTING.md")
        else:
            print("📖 Xem hướng dẫn xử lý lỗi trong file: TROUBLESHOOTING.md")
        
        print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    main()
