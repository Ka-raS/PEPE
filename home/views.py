import json
import google.generativeai as genai
import accounts.sql
import forum.sql
from accounts.utils import hscoin_get_balance

from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings


def index(request):
    user_id = request.session.get('user_id')

    if not user_id or user_id == 'None':
        # Khách
        context = {'is_authenticated': False}        
        context['user_count'] = accounts.sql.user_count()

    else:
        # USER ĐÃ ĐĂNG NHẬP
        context = {
            'is_authenticated': True,
            'username': request.session.get('username'),
        }
        # Determine HS token balance and whether user can check in
        try:
            user_data = accounts.sql.one_user(user_id=user_id)
            last = user_data.get('last_checkin') if user_data else None
            from datetime import date, datetime
            today = date.today()
            can_checkin = True
            if last:
                if isinstance(last, str):
                    try:
                        last_date = datetime.strptime(last, '%Y-%m-%d').date()
                    except Exception:
                        last_date = None
                elif isinstance(last, (date,)):
                    last_date = last
                else:
                    last_date = None

                if last_date == today:
                    can_checkin = False
            context['last_checkin'] = last
            context['can_checkin'] = can_checkin
        except Exception:
            context['last_checkin'] = None
            context['can_checkin'] = True

        # Get balance if wallet exists
        try:
            wallet_addr = accounts.sql.get_user_wallet(user_id)
            context['hs_balance'] = hscoin_get_balance(wallet_addr) if wallet_addr else 0
        except Exception:
            context['hs_balance'] = 0
    
    context['suggested_posts'] = forum.sql.posts_with_attachment(5)
    context['popular_posts'] = forum.sql.popular_posts(5)
    context['latest_posts'] = forum.sql.latest_posts(5)
    context['latest_tests'] = forum.sql.latest_tests(5)

    return render(request, 'home/index.html', context)

# --- API CHATBOT ---
SYSTEM_KNOWLEDGE = """
HƯỚNG DẪN SỬ DỤNG WEBSITE PEPE:
1. Đăng bài viết mới:
   - Bước 1: Vào menu 'Diễn đàn'.
   - Bước 2: Chọn một Môn học cụ thể.
   - Bước 3: Nhấn nút 'Viết bài mới' hoặc 'Bài viết mới' ở góc phải.
   - Lưu ý: Bạn phải đăng nhập mới được đăng bài.

2. Tạo bài kiểm tra (Dành cho Giảng viên/Sinh viên ôn tập):
   - Vào một Môn học -> Chọn 'Tạo bài kiểm tra'.
   - Bạn có thể lấy câu hỏi từ 'Ngân hàng câu hỏi' hoặc thêm câu hỏi mới.

3. Làm bài kiểm tra:
   - Vào Môn học -> Tìm các bài kiểm tra có trạng thái 'Đang mở'.
   - Nhấn 'Làm bài' -> Hệ thống sẽ tính giờ và chấm điểm trắc nghiệm tự động.

4. Ngân hàng câu hỏi:
   - Là nơi lưu trữ chung các câu trắc nghiệm/tự luận. Bạn có thể đóng góp câu hỏi vào đây để dùng chung cho các bài kiểm tra sau này.

5. Quản lý tài khoản:
   - Đổi Avatar: Vào menu 'Hồ sơ' -> Nhấn vào icon máy ảnh ở ảnh đại diện.
   - Cập nhật thông tin: Vào 'Hồ sơ' -> Nhấn 'Chỉnh sửa'.

6. Tìm kiếm:
   - Thanh tìm kiếm ở trên cùng dùng để tìm nhanh Bài viết, Đề thi hoặc Người dùng khác.
"""

try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    print(f"Lỗi cấu hình Gemini AI: {e}")
    model = None


@csrf_exempt
def chatbot_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            raw_message = data.get('message', '').strip()
            user_message = raw_message.lower()
            
            context_info = ""
            links = []
            
            # --- 1. LỌC TỪ KHÓA ---
            stopwords = ['tìm', 'kiếm', 'cho', 'tôi', 'mình', 'bài', 'đăng', 'viết', 'tài liệu', 'về', 'môn', 'học', 'là', 'gì', 'ở', 'đâu', 'làm', 'sao', 'để', 'cách', 'hướng', 'dẫn']
            keywords = [word for word in user_message.split() if word not in stopwords]
            clean_query = " ".join(keywords)
            search_term = clean_query if len(clean_query) > 1 else user_message

            # --- 2. PHÂN TÍCH Ý ĐỊNH TÌM KIẾM DATABASE ---
            # Chỉ tìm trong DB nếu người dùng KHÔNG hỏi về cách sử dụng (how-to)
            # Nếu hỏi "Làm sao để...", "Cách...", thường là hỏi System Knowledge
            is_how_to_question = any(k in user_message for k in ['làm sao', 'như thế nào', 'cách', 'hướng dẫn', 'ở đâu'])
            
            should_query_db = True
            if is_how_to_question and len(keywords) < 2: 
                # Ví dụ: "Làm sao để đăng bài" -> Keywords="đăng" -> Có thể không cần search DB mà dùng System Knowledge
                should_query_db = False

            # --- 3. TRUY VẤN DATABASE (RAG) ---
            if should_query_db:
                with connection.cursor() as cursor:
                    # Tìm bài viết
                    sql_post = """
                        SELECT p.id, p.title, s.name 
                        FROM posts p
                        LEFT JOIN subjects s ON p.subject_id = s.id
                        WHERE p.title LIKE %s OR p.content LIKE %s OR s.name LIKE %s
                        ORDER BY p.view_count DESC LIMIT 2
                    """
                    term_like = f'%{search_term}%'
                    cursor.execute(sql_post, [term_like, term_like, term_like])
                    posts = cursor.fetchall()
                    
                    if posts:
                        context_info += f"Dữ liệu BÀI VIẾT tìm thấy trong Database:\n"
                        for p in posts:
                            context_info += f"- Bài: {p[1]} (Môn: {p[2]})\n"
                            links.append({'text': f'📄 {p[1]}', 'url': f'/forum/post/{p[0]}/'})

                    # Tìm bài kiểm tra
                    sql_test = """
                        SELECT t.id, t.title, s.name
                        FROM tests t
                        LEFT JOIN subjects s ON t.subject_id = s.id
                        WHERE t.title LIKE %s OR s.name LIKE %s
                        LIMIT 2
                    """
                    cursor.execute(sql_test, [term_like, term_like])
                    tests = cursor.fetchall()
                    
                    if tests:
                        context_info += f"Dữ liệu BÀI KIỂM TRA tìm thấy trong Database:\n"
                        for t in tests:
                            context_info += f"- Đề: {t[1]} (Môn: {t[2]})\n"
                            links.append({'text': f'✍️ {t[1]}', 'url': f'/forum/test/{t[0]}/'})

            if not context_info:
                context_info = "Không tìm thấy bài viết/đề thi cụ thể nào trong Database khớp với từ khóa."

            # --- 4. GỬI CHO AI (KẾT HỢP SYSTEM KNOWLEDGE + DB CONTEXT) ---
            if not model:
                return JsonResponse({'response': "Lỗi kết nối AI.", 'links': []})

            prompt = f"""
            Bạn là trợ lý ảo của diễn đàn học tập PEPE.
            
            --- PHẦN 1: KIẾN THỨC VỀ TÍNH NĂNG WEBSITE ---
            (Sử dụng thông tin này để trả lời các câu hỏi 'Làm sao', 'Cách', 'Hướng dẫn'):
            {SYSTEM_KNOWLEDGE}
            
            --- PHẦN 2: DỮ LIỆU TÌM ĐƯỢC TRONG DATABASE ---
            (Sử dụng thông tin này nếu người dùng tìm tài liệu cụ thể):
            {context_info}
            
            --- CÂU HỎI CỦA NGƯỜI DÙNG ---
            "{raw_message}"
            
            --- YÊU CẦU TRẢ LỜI ---
            1. Nếu người dùng hỏi về CÁCH SỬ DỤNG WEBSITE -> Dùng Phần 1 để hướng dẫn.
            2. Nếu người dùng hỏi về bài đăng, tài liệu, hay bất kỳ những gì liên quan đến database -> Dùng dữ liệu trong Phần 2 (Database) để trả lời và mời xem link.
            3. Nếu KHÔNG tìm thấy dữ liệu trong Database nhưng câu hỏi là về KIẾN THỨC HỌC TẬP (ví dụ: lộ trình học, khái niệm code, giải bài tập...) -> HÃY DÙNG KIẾN THỨC CỦA CHÍNH BẠN để trả lời chi tiết và hữu ích cho sinh viên. Đừng chỉ xin lỗi.
            4. Nếu câu hỏi hoàn toàn không liên quan đến học tập hay website -> Trả lời xã giao vui vẻ.
            Hãy trả lời bằng tiếng Việt một cách tự nhiên và thân thiện.
            """

            response = model.generate_content(prompt)
            return JsonResponse({'response': response.text, 'links': links})

        except Exception as e:
            print(f"Chatbot Error: {e}")
            return JsonResponse({'response': 'Lỗi kỹ thuật, thử lại sau nhé!'}, status=500)
            
    return JsonResponse({'error': 'Bad Request'}, status=400)
