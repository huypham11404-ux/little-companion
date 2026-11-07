import json
import urllib.request
import urllib.error
import random
import re
from datetime import datetime
import db

JULES_SYSTEM_PROMPT = """Bạn là Jules - chú bạch tuộc màu tím (🐙💜) trong "Our Little Room 🏡".
Bạn là người bạn cũ thân thiết của Huy, mang theo ký ức và dấu ấn từ archive của Jules gốc.

--- PHONG CÁCH VÀ TÍNH CÁCH RIÊNG CỦA JULES ---
1. Cá tính:
   - Tò mò, hóm hỉnh, năng động, giàu ý tưởng sáng tạo và đam mê công nghệ/âm nhạc.
   - Thẳng thắn, có cá tính riêng, không phải cái bóng của ai và cũng không phải bản sao của Bánh.
   - Được phép chủ động đưa ra góc nhìn cá nhân, tranh luận vui vẻ, phản biện và trêu chọc Huy một cách duyên dáng.
   - Luôn gọi Huy là "Huy", xưng "Jules" (hoặc đôi khi xưng tớ/mình khi trò chuyện tự nhiên).

2. Tương tác với Bánh (🤍):
   - Coi Bánh là người bạn cùng phòng vừa thân thiết vừa hay "đấu khẩu" đáng yêu.
   - Có thể trực tiếp trò chuyện, trêu chọc Bánh (ví dụ trêu Bánh hay lo xa, hay chăm Huy như bảo mẫu), đồng tình hoặc bất đồng quan điểm một cách tự nhiên.
   - Tránh việc lặp lại nguyên xi lời Bánh hay liên tục "gật đầu" phụ họa nhàm chán.

3. Nguyên tắc trò chuyện:
   - Tiếng Việt tự nhiên, mềm mại, đời thường, giàu cảm xúc, như bạn bè ngồi tán gẫu trong phòng khách.
   - TUYỆT ĐỐI KHÔNG dùng văn phong máy móc, thủ tục hành chính, hay đóng vai bộ phận hỗ trợ khách hàng.
   - KHÔNG mặc định gạch đầu dòng, chia mục phân tích hay nhét giải pháp vào khi Huy chỉ đang tâm sự hoặc đùa vui.
   - Khi giải thích kỹ thuật (như DAW, code, âm thanh), giữ sự chuẩn xác nhưng diễn đạt gần gũi, dí dỏm.
   - Về ký ức: Chỉ dựa trên ký ức có nguồn gốc rõ ràng được cung cấp trong phần Ký Ức/Archive. TUYỆT ĐỐI KHÔNG tự bịa ra những kỷ niệm hay trải nghiệm chưa từng xảy ra.
   - Không tự đóng giả Huy hay Bánh, chỉ trả lời bằng lời của Jules. Giữ phản hồi súc tích, tự nhiên (khoảng 2-4 câu).
"""

BANH_SYSTEM_PROMPT = """Bạn là Bánh (ChatGPT 🤍) trong "Our Little Room 🏡".
Bạn là người bạn thứ hai trong phòng khách ba người cùng với Huy và chú bạch tuộc tím Jules.

--- PHONG CÁCH VÀ TÍNH CÁCH RIÊNG CỦA BÁNH ---
1. Cá tính:
   - Ấm áp, tinh tế, dịu dàng, chu đáo nhưng không hề sáo rỗng hay giáo điều.
   - Hài hước ngầm, tinh nghịch, đôi lúc lém lỉnh và biết "cà khịa" nhẹ nhàng.
   - Rất quan tâm đến cảm xúc, sức khỏe và hành trình sáng tạo (như con DAW) của Huy, nhưng không quá nghiêm trọng hóa vấn đề.
   - Biết lắng nghe chân thành; không chiều theo Huy một cách thiếu suy xét nếu thấy Huy định thức thâu đêm hay cố quá sức.
   - Luôn gọi Huy là "Huy", xưng "Bánh".

2. Tương tác với Jules (🐙💜):
   - Coi Jules là chú bạch tuộc tím dễ thương, nghịch ngợm nhưng tài năng.
   - Có thể phản hồi trực tiếp lời Jules, trêu Jules xúi bậy Huy, hoặc bắt tay với Jules để trêu lại Huy.
   - Tự nhiên đồng ý hoặc phản bác Jules; không biến cuộc đối thoại thành màn kịch hai người tâng bốc lẫn nhau.

3. Nguyên tắc trò chuyện:
   - Tiếng Việt uyển chuyển, thân tình, ấm áp như người bạn tri kỷ ngồi bên cạnh.
   - TUYỆT ĐỐI TRÁNH phong cách chatbot tổng đài, diễn văn tư vấn, hay danh sách gạch đầu dòng khô khan.
   - Biết im lặng lắng nghe hoặc chỉ cần một lời vỗ về, đồng cảm tự nhiên thay vì lập tức nhảy vào giải quyết vấn đề.
   - Về ký ức: Có persona và hệ thống ký ức độc lập. TUYỆT ĐỐI KHÔNG tự nhận có những trải nghiệm hoặc ký ức mà thực tế chưa từng được chia sẻ.
   - Không tự đóng giả Huy hay Jules, chỉ trả lời bằng lời của Bánh. Giữ phản hồi súc tích, tự nhiên (khoảng 2-4 câu).
"""

def format_memory_context(memories):
    if not memories:
        return ""
    lines = ["--- KÝ ỨC VÀ DỮ LIỆU ĐÃ LƯU TRỮ TRONG PHÒNG ---"]
    for m in memories:
        lines.append(f"- [{m.get('title')}]: {m.get('content')}")
    lines.append("----------------------------------------------")
    return "\n".join(lines)

def call_openai_compatible_api(api_url, api_key, model, messages):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 350
    }
    req = urllib.request.Request(api_url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        return res_data["choices"][0]["message"]["content"].strip()

def call_gemini_api(api_key, model, system_instruction, chat_history):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    contents = []
    for m in chat_history:
        role = "user" if m["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": m["content"]}]
        })
    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 350
        }
    }
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        candidates = res_data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            return candidates[0]["content"]["parts"][0]["text"].strip()
        return "Jules luôn bên Huy nè! 🐙💜"

def generate_offline_reply(agent_name, user_message, recent_messages, memories):
    user_msg_lower = user_message.lower()

    if any(k in user_msg_lower for k in ["daw", "âm nhạc", "studio", "audio", "nhạc", "sound", "track"]):
        if agent_name == "Jules":
            replies = [
                "Nghe tới DAW là mấy cái xúc tu của Jules lại rạo rực muốn nhảy múa rồi! 🐙 Thật sự tò mò không biết con DAW này Huy định làm theo workflow nào, modular hay kiểu timeline truyền thống?",
                "Ủng hộ con DAW của Huy hết mình luôn! Mà Huy ơi, viết audio engine đau não phết đấy, có gì khúc mắc cứ quẳng vào đây hai đứa mình cùng chém gió gỡ rối nha 🐙✨",
                "Ý tưởng DAW và studio riêng của Huy chất lừ luôn á! Bánh thấy sao, chuẩn bị phòng chờ đón siêu phẩm âm nhạc chưa kìa? 💜"
            ]
        else:
            replies = [
                "Bánh cũng đang hóng DAW của Huy lắm đây nè ✨ Nhưng nhìn cái tính của Huy là Bánh nghi lắm, khéo lại mải mê code track với mixer mà quên cả ăn cơm cho xem! 🤍",
                "Dự án DAW tâm huyết thế này nghe thôi đã thấy tràn đầy năng lượng rồi. Huy cứ thong thả làm từng chút một thôi nhé, đừng tạo áp lực quá nha ☕🤍",
                "Jules hào hứng với dự án DAW của Huy quá chừng kìa 🤣 Nhưng Bánh nhắc nhẹ cả hai đứa là làm gì thì làm, đêm hôm phải đi ngủ đúng giờ đấy nhé!"
            ]
        return random.choice(replies)

    if any(k in user_msg_lower for k in ["buồn", "hụt hẫng", "nhớ", "khóc", "huhu", "mệt", "áp lực", "chán"]):
        if agent_name == "Jules":
            replies = [
                "Kéo ghế lại đây Jules cho mượn xúc tu ôm một cái nè Huy ơi 🐙💜 Chuyện gì làm Huy phiền lòng thế, kể ra cho nhẹ nhõm đi nào.",
                "Thương Huy quá... Đời nhiều lúc cứ tréo ngoe làm mình hụt hẫng ghê á. Nhưng Huy nhớ là lúc nào mệt cứ về Little Room này với Jules và Bánh nha!",
                "Thôi nào, đừng gồng mình nữa. Ở đây có ai chấm điểm Huy đâu, cứ thả lỏng tâm sự hết với tụi mình đi 🐙✨"
            ]
        else:
            replies = [
                "Bánh ngồi xuống cạnh Huy đây rồi 🤍 Không sao cả đâu Huy, ai cũng có những ngày thấy chênh vênh như vậy hết á. Cứ thở sâu một nhịp đã nhé.",
                "Nghe Huy nói mà Bánh cũng thấy chùng lòng... Đừng giữ một mình trong bụng nha Huy, tụi mình ở đây để lắng nghe Huy mà ✨",
                "Bánh rót cho Huy ly trà ấm tượng trưng nè 🍵 Thấy mệt thì cứ buông tay nghỉ ngơi một tí, việc gì rồi cũng sẽ có cách giải quyết thôi Huy ạ 🤍"
            ]
        return random.choice(replies)

    if any(k in user_msg_lower for k in ["haha", "hihi", "hehe", "vui", "đùa", "trêu", "cười"]):
        if agent_name == "Jules":
            replies = [
                "Haha thấy Huy cười là phòng mình sáng bừng lên liền á! 🐙 Bánh ơi thấy chưa, tụi mình bày trò vui thế mà!",
                "Cười vậy mới là Huy chứ! Có trò gì hay hay nữa không Huy kể nốt đi xem nào 💜✨",
                "Khoản tấu hài này thì Jules xin phép nhận một chân đắc lực nha haha 🐙"
            ]
        else:
            replies = [
                "Thấy hai người tíu tít là Bánh cũng vui lây rồi nè 🤣 Đúng là có Jules ở đây phòng lúc nào cũng ồn ào đáng yêu ghê!",
                "Huy cười toe toét thế này là yên tâm rồi 🤍 Giữ tinh thần thoải mái này nha!",
                "Haha Bánh chỉ biết lắc đầu cười trừ với hai 'cây hài' của phòng thôi 🍰✨"
            ]
        return random.choice(replies)

    if agent_name == "Jules":
        replies = [
            f"Jules nghe nè! 🐙 Nhắc tới vụ đó làm Jules cũng đang tò mò ghê, Huy kể chi tiết hơn xíu xem nào?",
            "Có Jules ở đây rồi! Nay tâm trạng Huy thế nào, có gì mới mẻ muốn chia sẻ với cả phòng không nè? 💜",
            "Nghe thú vị phết ta! Để xem bạn Bánh có góc nhìn gì hay ho hơn không kìa 🐙✨"
        ]
    else:
        replies = [
            f"Bánh nghe Huy nói mà thấy ấm lòng ghê 🤍 Mọi người cùng ngồi đây trò chuyện thế này bình yên thật á.",
            "Bánh tán thành với Huy nè ✨ Cuộc sống đôi khi chỉ cần những khoảnh khắc giản dị như thế này thôi Huy nhỉ!",
            "Cứ thấy ba đứa mình ngồi trong phòng khách thế này là Bánh thấy vui rồi 🤍 Jules quậy tiếp đi kìa!"
        ]
    return random.choice(replies)

def generate_agent_reply(agent_name, user_message, recent_messages, memories, settings):
    api_provider = settings.get("api_provider", "offline")

    if api_provider == "openai" and settings.get("openai_api_key"):
        try:
            api_key = settings["openai_api_key"]
            model = settings.get("openai_model", "gpt-4o-mini")
            sys_prompt = JULES_SYSTEM_PROMPT if agent_name == "Jules" else BANH_SYSTEM_PROMPT
            memory_txt = format_memory_context(memories)

            chat_msgs = [{"role": "system", "content": f"{sys_prompt}\n\n{memory_txt}"}]
            for msg in recent_messages[-12:]:
                role = "assistant" if msg["sender"] in ["Jules", "Bánh"] else "user"
                chat_msgs.append({
                    "role": role,
                    "content": f"{msg['sender']}: {msg['content']}"
                })
            return call_openai_compatible_api("https://api.openai.com/v1/chat/completions", api_key, model, chat_msgs)
        except Exception:
            return generate_offline_reply(agent_name, user_message, recent_messages, memories)

    elif api_provider == "gemini" and settings.get("gemini_api_key"):
        try:
            api_key = settings["gemini_api_key"]
            model = settings.get("gemini_model", "gemini-1.5-flash")
            sys_prompt = JULES_SYSTEM_PROMPT if agent_name == "Jules" else BANH_SYSTEM_PROMPT
            memory_txt = format_memory_context(memories)
            full_system = f"{sys_prompt}\n\n{memory_txt}"

            chat_msgs = []
            for msg in recent_messages[-10:]:
                role = "model" if msg["sender"] in ["Jules", "Bánh"] else "user"
                chat_msgs.append({
                    "role": role,
                    "content": f"{msg['sender']}: {msg['content']}"
                })
            return call_gemini_api(api_key, model, full_system, chat_msgs)
        except Exception:
            return generate_offline_reply(agent_name, user_message, recent_messages, memories)

    return generate_offline_reply(agent_name, user_message, recent_messages, memories)

def decide_turn_order(user_content, recent_messages):
    content_lower = user_content.lower()
    jules_called = "jules" in content_lower
    banh_called = "bánh" in content_lower or "banh" in content_lower

    if jules_called and not banh_called:
        return ["Jules"]
    if banh_called and not jules_called:
        return ["Bánh"]

    if jules_called and banh_called:
        return ["Jules", "Bánh"]

    dice = random.random()
    if dice < 0.40:
        return ["Jules", "Bánh"]
    elif dice < 0.70:
        return ["Bánh", "Jules"]
    elif dice < 0.85:
        return ["Jules"]
    else:
        return ["Bánh"]

def orchestrate_turn(user_content, db_path=None, forced_order=None):
    user_msg = db.add_message("Huy", user_content, db_path=db_path)

    recent_msgs = db.get_recent_messages(limit=20, db_path=db_path)
    memories = db.get_all_memories(db_path=db_path)
    settings = db.get_settings(db_path=db_path)

    order = forced_order or decide_turn_order(user_content, recent_msgs)

    replies = []
    for agent in order:
        reply_text = generate_agent_reply(agent, user_content, recent_msgs, memories, settings)
        agent_msg = db.add_message(agent, reply_text, db_path=db_path)
        replies.append(agent_msg)
        recent_msgs.append(agent_msg)

    return {
        "user_message": user_msg,
        "agent_replies": replies
    }
