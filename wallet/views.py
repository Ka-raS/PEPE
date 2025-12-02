from datetime import date
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.db import connection

def wallet(request):
    """Ví điểm - dùng session thay vì Django auth (không dùng ORM)"""
    if not request.session.get('user_id'):
        messages.error(request, 'Vui lòng đăng nhập để xem ví')
        return redirect('accounts:login')

    username = request.session.get('username', '')
    user_id = request.session.get('user_id')

    # Lấy thông tin ví (student) để hiển thị wallet address nếu đã liên kết (raw SQL)
    has_wallet = False
    wallet_address = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT wallet_address FROM students WHERE id = %s", [user_id])
        row = cursor.fetchone()
        if row and row[0]:
            has_wallet = True
            wallet_address = row[0]

    # Tạo referral link
    referral_link = "#"
    try:
        scheme = request.scheme
        domain = request.get_host()
        register_url = reverse('accounts:register')
        referral_link = f"{scheme}://{domain}{register_url}?ref={username}"
    except Exception as e:
        print(f"Lỗi tạo link giới thiệu: {e}")

    # Lấy lịch sử giao dịch (nếu có)
    transaction_history = []
    try:
        from accounts.utils import read_user_txs
        transaction_history = read_user_txs(user_id, limit=50)
    except Exception:
        transaction_history = []

    context = {
        'username': username,
        'referral_link': referral_link,
        'transactions': transaction_history,
        'is_authenticated': True,
        'has_wallet': has_wallet,
        'wallet_address': wallet_address,
    }
    return render(request, 'wallet/index.html', context)


def referral(request):
    """Trang giới thiệu - dùng session, không dùng ORM"""
    if not request.session.get('user_id'):
        messages.error(request, 'Vui lòng đăng nhập')
        return redirect('accounts:login')
    
    username = request.session.get('username', '')
    user_id = request.session.get('user_id')
    
    # Tạo link giới thiệu
    referral_link = "#"
    try:
        scheme = request.scheme
        domain = request.get_host()
        register_url = reverse('accounts:register')
        referral_link = f"{scheme}://{domain}{register_url}?ref={username}"
    except Exception as e:
        print(f"Lỗi tạo link giới thiệu: {e}")
    
    # Lấy dữ liệu giới thiệu từ DB (raw SQL)
    referrals_made_count = 0
    coins_earned = 0
    recent_referrals_list = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.username, r.created_at
                FROM referrals r
                JOIN users u ON r.referred_id = u.id
                WHERE r.referrer_id = %s AND r.rewarded_referrer = 1
                ORDER BY r.created_at DESC
                LIMIT 10
            """, [user_id])
            rows = cursor.fetchall()
            recent_referrals_list = [
                {'username': row[0], 'date_joined': row[1]}
                for row in rows
            ]
            # Đếm tổng số lượt giới thiệu thành công
            cursor.execute("""
                SELECT COUNT(*) FROM referrals
                WHERE referrer_id = %s AND rewarded_referrer = 1
            """, [user_id])
            referrals_made_count = cursor.fetchone()[0]
            coins_earned = referrals_made_count * 50
    except Exception:
        referrals_made_count = 0
        coins_earned = 0
        recent_referrals_list = []
    
    context = {
        'username': username,
        'referral_link': referral_link,
        'referrals_made_count': referrals_made_count,
        'coins_earned_from_referrals': coins_earned,
        'recent_referrals_list': recent_referrals_list,
        'is_authenticated': True,
    }
    return render(request, 'wallet/referral.html', context)


def checkin_view(request):
    """Điểm danh hằng ngày - nhận coin (raw SQL, không dùng ORM)"""
    if request.method != 'POST':
        return redirect('home:index')
    
    if not request.session.get('user_id'):
        messages.error(request, 'Vui lòng đăng nhập để điểm danh')
        return redirect('accounts:login')
    
    user_id = request.session.get('user_id')
    COIN_REWARD = 5
    today = date.today()

    # Lấy thông tin last_checkin và coins từ DB
    with connection.cursor() as cursor:
        cursor.execute("SELECT last_checkin FROM users WHERE id = %s", [user_id])
        row = cursor.fetchone()
        last_checkin = row[0] if row else None

    if last_checkin == today:
        messages.error(request, 'Bạn đã điểm danh hôm nay rồi!')
    else:
        # Cộng coin và cập nhật last_checkin
        with connection.cursor() as cursor:
            cursor.execute("SELECT coins FROM users WHERE id = %s", [user_id])
            row = cursor.fetchone()
            coins = row[0] if row and row[0] is not None else 0
            new_coins = coins + COIN_REWARD
            cursor.execute(
                "UPDATE users SET coins = %s, last_checkin = %s WHERE id = %s",
                [new_coins, today, user_id]
            )
        messages.success(request, f'Bạn đã điểm danh thành công và nhận được {COIN_REWARD} coin!')

    return redirect('home:index')