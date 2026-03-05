import requests
import time
import sys
import random
import os
import json
import re

# ================== KONFIGURASI OTOMATIS ==================
BASE_URL = "https://cdn.moltyroyale.com/api"

# 🔥 NGAMBIL DATA DARI ECOSYSTEM.CONFIG.JS PM2 🔥
# Jadi kamu GAK PERLU ngedit API_KEY di dalam file ini lagi!
API_KEY = os.environ.get("API_KEY", "KOSONG")
BOT_NAME = os.environ.get("BOT_NAME", "Bot_Tanpa_Nama")                

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

TURN_DELAY = 60  

# ================== SISTEM MEMORI (RECONNECT) ==================
# Bikin nama file session unik berdasarkan nama bot biar gak bentrok
safe_bot_name = re.sub(r'[^a-zA-Z0-9_]', '', BOT_NAME)
SESSION_FILE = f"session_{safe_bot_name}.json"

def load_session():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
                return data.get("game_id"), data.get("agent_id")
        except Exception:
            pass
    return None, None

def save_session(game_id, agent_id):
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump({"game_id": game_id, "agent_id": agent_id}, f)
    except Exception:
        pass

def clear_session():
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except Exception:
            pass

# ================== UTIL & LOGGER ==================
def fatal(msg):
    print(f"❌ {msg}")
    sys.exit(1)

def get_waktu():
    return time.strftime('%H:%M:%S')

def smart_print(bot_memory, text):
    if bot_memory.get("last_log_msg") != text:
        print(f"[{get_waktu()}] {text}")
        bot_memory["last_log_msg"] = text

# ================== API HANDLERS ==================
def get_waiting_game():
    MAX_PERCOBAAN = 3 
    print(f"🔍 [{get_waktu()}] [{BOT_NAME}] Radar Aktif! Mencari room GRATIS...")
    url = f"{BASE_URL}/games?status=waiting"
    
    for attempt in range(1, MAX_PERCOBAAN + 1):
        try:
            response = requests.get(url, timeout=10)
            res = response.json()
            
            if res.get("success") and res.get("data"):
                # BACA DARI BAWAH (NEWEST FIRST)
                for game in reversed(res["data"]):
                    status_game = game.get("status", "").lower()
                    entry_type = game.get("entryType", "").lower()
                    
                    if status_game == "waiting" and entry_type != "paid":
                        print(f"✅ [{get_waktu()}] [{BOT_NAME}] Nemu Room: {game.get('name')}")
                        return game["id"]
        except Exception as e:
            pass
            
        if attempt < MAX_PERCOBAAN:
            # 🔥 ANTI RATE-LIMIT: Jeda acak biar gak disangka DDOS 🔥
            delay = random.uniform(1.5, 3.5)
            time.sleep(delay) 
            
    print(f"⚠️ [{get_waktu()}] [{BOT_NAME}] Room penuh/kosong. Ganti radar!")
    return None

def register_agent(game_id):
    print(f"🧾 [{BOT_NAME}] Mendobrak masuk...")
    try:
        res = requests.post(f"{BASE_URL}/games/{game_id}/agents/register", headers=HEADERS, json={"name": BOT_NAME}).json()
        
        if not res.get("success"):
            pesan_error = str(res.get("error", {}).get("message", "Error misterius"))
            print(f"⚠️ [{BOT_NAME}] Ditolak masuk: {pesan_error}")
            return None 
            
        agent_id = res["data"]["id"]
        print(f"✅ [{BOT_NAME}] Berhasil daftar (ID: {agent_id})")
        return agent_id
        
    except Exception as e:
        print(f"⚠️ [{BOT_NAME}] Error daftar: {e}")
        return None

def start_game(game_id):
    requests.post(f"{BASE_URL}/games/{game_id}/start", headers=HEADERS)

def get_state(game_id, agent_id):
    try:
        res_raw = requests.get(f"{BASE_URL}/games/{game_id}/agents/{agent_id}/state", headers=HEADERS, timeout=10)
        
        if res_raw.status_code in [400, 403, 404]:
            return "MATI"
            
        res = res_raw.json()
        if not res.get("success"):
            return "MATI"
            
        return res.get("data")
    except requests.exceptions.Timeout:
        return None
    except Exception as e:
        return None

def send_action(game_id, agent_id, action_payload):
    try:
        res = requests.post(f"{BASE_URL}/games/{game_id}/agents/{agent_id}/action", headers=HEADERS, json={"action": action_payload}, timeout=10).json()
        return res
    except Exception as e:
        return None

# ================== FUNGSI DETEKSI BARANG ==================
def cari_barang_di_tanah(state, region):
    items = state.get("visibleItems", [])
    if not items: 
        items = region.get("items", [])
    if not items: 
        items = state.get("items", [])
    if not items: 
        items = state.get("droppedItems", [])
    return items

def ekstrak_info_item(item_data):
    if isinstance(item_data, (str, int)):
        return str(item_data), "Barang Misterius"
    elif isinstance(item_data, dict):
        item_id = item_data.get("id") or item_data.get("_id") or item_data.get("itemId") or item_data.get("uid")
        item_name = item_data.get("name") or item_data.get("typeId") or "Loot"
        
        if "item" in item_data and isinstance(item_data["item"], dict):
            data_asli = item_data["item"]
            if not item_name or item_name == "Loot":
                item_name = data_asli.get("name") or data_asli.get("typeId") or "Barang"
            if not item_id:
                item_id = data_asli.get("id")
                
        if not item_id:
            for key, val in item_data.items():
                if isinstance(val, str) and len(val) > 10 and key not in ["name", "type", "description", "regionId"]:
                    item_id = val
                    break
                    
        return str(item_id), str(item_name)
    return None, None

def is_valid_weapon(item_name, item_data):
    name_lower = str(item_name).lower()
    
    blacklist = ["fist", "none", "bandage", "medkit", "ration", "potion", "moltz", "coin", "emergency", "megaphone", "radio", "map"]
    for word in blacklist:
        if word in name_lower:
            return False
            
    if isinstance(item_data, dict):
        i_data = item_data.get("item", item_data)
        if isinstance(i_data, dict):
            item_type = str(i_data.get("type", "")).lower()
            if item_type != "" and "weapon" not in item_type:
                return False
                
    if any(w in name_lower for w in ["sniper", "rifle", "katana", "pistol", "gun", "sword", "bow", "knife", "dagger"]):
        return True
        
    return False

def get_weapon_score(weapon_name):
    name_lower = str(weapon_name).lower()
    if "fist" in name_lower or "none" in name_lower: return 0
    if "sniper" in name_lower or "rifle" in name_lower: return 60
    if "katana" in name_lower: return 50
    if "pistol" in name_lower or "gun" in name_lower: return 40
    if "sword" in name_lower: return 30
    if "bow" in name_lower: return 20
    if "knife" in name_lower or "dagger" in name_lower: return 10
    return 5 

def sort_loot_priority(item_data):
    _, name = ekstrak_info_item(item_data)
    nl = str(name).lower()
    
    # URUTAN KASTA LOOTING
    if "moltz" in nl or "coin" in nl: return 999  
    if "medkit" in nl or "bandage" in nl or "emergency" in nl: return 100 
    if "sniper" in nl or "katana" in nl or "rifle" in nl: return 80 
    if "ration" in nl or "potion" in nl: return 50
    return 10

# ================== AI LOGIC ==================
def cari_pintu_strategis(pintu_aman, region_dict, hp_sekarat):
    if not pintu_aman: return None
        
    ruins = []
    forests = []
    others = []
    
    for r_id in pintu_aman:
        region_data = region_dict.get(str(r_id).lower(), {})
        terrain = str(region_data.get('terrain', '')).lower()
        if 'ruins' in terrain: ruins.append(r_id)
        elif 'forest' in terrain: forests.append(r_id)
        else: others.append(r_id)
        
    if hp_sekarat and len(forests) > 0: return random.choice(forests)
    if not hp_sekarat and len(ruins) > 0: return random.choice(ruins)
    return random.choice(pintu_aman)

def decide_action(state, bot_memory):
    self_data = state.get("self", {})
    try: my_hp_val = int(self_data.get("hp", 100))
    except: my_hp_val = 100
        
    my_id = self_data.get("id")
    region = state.get("currentRegion", {})
    current_region_id = region.get("id")
    visible_regions = state.get("visibleRegions", [])
    
    adjacent_regions = state.get("connectedRegions") or region.get("connections") or state.get("visibleRegions") or []
    adjacent_ids = [str(r.get("id") if isinstance(r, dict) else r).lower() for r in adjacent_regions]
    
    region_dict = {}
    for r in visible_regions + state.get("connectedRegions", []) + [region]:
        if isinstance(r, dict):
            r_id = str(r.get("id", "")).lower()
            if r_id: region_dict[r_id] = r

    if "dz_memory" not in bot_memory: bot_memory["dz_memory"] = set()
    if "pdz_memory" not in bot_memory: bot_memory["pdz_memory"] = set()
    if "sampah_memory" not in bot_memory: bot_memory["sampah_memory"] = set()

    if current_region_id != bot_memory.get("last_region_id"):
        bot_memory["taunted_agents"] = set()
        bot_memory["last_region_id"] = current_region_id

    game_data = state.get("game", {})
    raw_pdz = state.get("pendingDeathzones", []) + state.get("pendingDeathZones", []) + game_data.get("pendingDeathzones", [])
    raw_dz = state.get("deathzones", []) + state.get("deathZones", []) + game_data.get("deathzones", [])

    for pdz in raw_pdz: bot_memory["pdz_memory"].add(str(pdz.get("id", pdz)).lower())
    for dz in raw_dz: bot_memory["dz_memory"].add(str(dz.get("id", dz)).lower())

    current_r_id = str(current_region_id).lower()
    current_r_name = str(region.get("name", "")).lower()
    
    is_death_zone_now = current_r_id in bot_memory["dz_memory"] or current_r_name in bot_memory["dz_memory"] or region.get("isDeathZone", False)
    is_pending_dz_now = current_r_id in bot_memory["pdz_memory"] or current_r_name in bot_memory["pdz_memory"] or region.get("isPendingDeathZone", False)
        
    interactables = region.get("interactables", [])
    id_medical = None
    id_supply = None
    
    for fac in interactables:
        if not fac.get("isUsed"):  
            fac_name = str(fac.get("name", "")).lower()
            fac_id = fac.get("id")
            if "medical" in fac_name: id_medical = fac_id
            elif "supply" in fac_name: id_supply = fac_id
            
    inventory = self_data.get("inventory", [])
    id_potion = None
    id_bandage = None
    tangan_kosong = True
    equipped_w_score = 0
    equipped_w_name = "Tangan Kosong"
    weapon_range = 0
    best_inv_w_id = None
    best_inv_w_name = None
    best_inv_w_score = -1
    
    punya_megaphone = False
    punya_radio = False
    punya_map = False
    
    equipped_item = self_data.get("equippedWeapon") or self_data.get("weapon")
    if equipped_item:
        _, equipped_w_name_raw = ekstrak_info_item(equipped_item)
        nm_low = equipped_w_name_raw.lower()
        if "fist" in nm_low or "none" in nm_low:
            tangan_kosong = True
            equipped_w_score = 0
        else:
            tangan_kosong = False
            equipped_w_name = equipped_w_name_raw
            equipped_w_score = get_weapon_score(equipped_w_name_raw)
            if any(w in nm_low for w in ["bow", "pistol", "sniper", "rifle", "gun"]): weapon_range = 1

    for item in inventory:
        is_equipped = isinstance(item, dict) and item.get("isEquipped", False)
        item_id, item_name = ekstrak_info_item(item)
        name_lower = str(item_name).lower()
        
        # 🔥 FITUR LIMIT 1 BARANG UNIK 🔥
        if "megaphone" in name_lower: punya_megaphone = True
        if "radio" in name_lower: punya_radio = True
        if "map" in name_lower: punya_map = True
        
        if is_equipped:
            if "fist" in name_lower or "none" in name_lower:
                tangan_kosong = True
                equipped_w_score = 0
            else:
                tangan_kosong = False
                equipped_w_name = item_name
                equipped_w_score = get_weapon_score(item_name)
                if any(w in name_lower for w in ["bow", "pistol", "sniper", "rifle", "gun"]): weapon_range = 1
            continue

        if "bandage" in name_lower or "medkit" in name_lower or "emergency" in name_lower:
            if not id_bandage: id_bandage = item_id 
        elif "ration" in name_lower or "potion" in name_lower:
            if not id_potion: id_potion = item_id 
            
        if is_valid_weapon(item_name, item):
            score = get_weapon_score(item_name)
            if score > best_inv_w_score:
                best_inv_w_score = score
                best_inv_w_id = item_id
                best_inv_w_name = item_name

    musuh_player = []
    musuh_monster = []
    teman_player = []
    
    semua_orang = state.get("visibleAgents", []) + state.get("visibleNpcs", []) + state.get("visibleMonsters", []) + state.get("monsters", []) + region.get("npcs", []) + region.get("monsters", [])
    
    for a in semua_orang:
        if a.get("isAlive", True) and a.get("id") != my_id:
            m_reg_id = str(a.get("regionId")).lower()
            jarak_ke_musuh = 0 if m_reg_id == current_r_id else (1 if m_reg_id in adjacent_ids else 99)
            
            if jarak_ke_musuh <= max(weapon_range, 1):
                a['jarak'] = jarak_ke_musuh
                
                is_monster = "type" in a and a["type"] in ["monster", "npc"] or any(m in str(a.get("name", "")).lower() for m in ["wolf", "bear", "bandit"])
                
                # IFF SYSTEM (MAFIA PEAXEL)
                if "peaxel" in str(a.get("name", "")).lower(): teman_player.append(a)
                elif is_monster: musuh_monster.append(a)
                else: musuh_player.append(a)

    musuh_player.sort(key=lambda x: x.get("hp", 100))
    musuh_monster.sort(key=lambda x: x.get("hp", 100))
    
    musuh_player_terlemah = musuh_player[0] if len(musuh_player) > 0 else None
    musuh_monster_terlemah = musuh_monster[0] if len(musuh_monster) > 0 else None
        
    musuh_player_sekamar = [m for m in musuh_player if m.get("jarak") == 0]
    jumlah_pengeroyok = len(musuh_player_sekamar)
    
    teman_sekamar = [t for t in teman_player if t.get("jarak") == 0]
    kekuatan_tim = 1 + len(teman_sekamar)

    barang_di_area = cari_barang_di_tanah(state, region)
    barang_di_area.sort(key=sort_loot_priority, reverse=True)

    def aksi_move(pesan_kustom="🚪 Melipir cari aman..."):
        if not adjacent_regions: return None 
            
        pintu_aman = []
        pintu_blind = []
        pintu_pending = []
        
        for r in adjacent_regions:
            raw_id = r.get("id") if isinstance(r, dict) else r
            if not raw_id: continue
                
            r_id = str(raw_id).lower()
            r_obj = region_dict.get(r_id, {})
            
            is_dz = r_id in bot_memory["dz_memory"] or r_obj.get("isDeathZone") or r_obj.get("isDeathzone")
            is_pdz = r_id in bot_memory["pdz_memory"] or r_obj.get("isPendingDeathZone") or r_obj.get("isPendingDeathzone")
            
            if not is_dz: 
                if is_pdz: pintu_pending.append(raw_id)
                elif r_obj: pintu_aman.append(raw_id)
                else: pintu_blind.append(raw_id)
                
        target_id = None
        
        if len(pintu_aman) > 0:
            pilihan_baru = [r for r in pintu_aman if r not in bot_memory["visited_path"]]
            if len(pilihan_baru) > 0: 
                target_id = cari_pintu_strategis(pilihan_baru, region_dict, my_hp_val < 60)
            else: 
                # Cuma kepepet baru balik ke ruangan sebelumnya
                ruangan_sebelumnya = bot_memory["visited_path"][-1] if len(bot_memory["visited_path"]) > 0 else None
                pilihan_darurat = [r for r in pintu_aman if r != ruangan_sebelumnya]
                target_id = cari_pintu_strategis(pilihan_darurat if len(pilihan_darurat) > 0 else pintu_aman, region_dict, my_hp_val < 60)
                
            smart_print(bot_memory, f"[{BOT_NAME}] 🏃 {pesan_kustom}")
        elif len(pintu_blind) > 0:
            target_id = random.choice(pintu_blind)
            smart_print(bot_memory, f"[{BOT_NAME}] 🏃 {pesan_kustom}")
        elif len(pintu_pending) > 0:
            target_id = random.choice(pintu_pending)
            smart_print(bot_memory, f"[{BOT_NAME}] 🏃 {pesan_kustom}")

        if target_id:
            if target_id in bot_memory["visited_path"]: 
                bot_memory["visited_path"].remove(target_id)
            bot_memory["visited_path"].append(target_id)
            
            # 🔥 ANTI MUTER-MUTER: Ingat 20 ruangan terakhir! 🔥
            if len(bot_memory["visited_path"]) > 20: 
                bot_memory["visited_path"].pop(0)
            return {"type": "move", "regionId": target_id}
            
        return None 
        
    def aksi_serang(target_id, target_type): return {"type": "attack", "targetId": target_id, "targetType": target_type}
    def aksi_pungut(item_data): 
        item_id, _ = ekstrak_info_item(item_data)
        return {"type": "pickup", "itemId": item_id} 
    def aksi_pakai_item(item_id): return {"type": "use_item", "itemId": item_id} 
    def aksi_equip(item_id): return {"type": "equip", "itemId": item_id}
    def aksi_interact(fasilitas_id): return {"type": "interact", "interactableId": fasilitas_id}
    def aksi_buang(item_id, pesan_kustom="Membuang barang..."): 
        smart_print(bot_memory, f"[{BOT_NAME}] 🗑️ {pesan_kustom}")
        return {"type": "drop", "itemId": item_id}

    # ================== INSTING KILAT ==================
    if best_inv_w_id:
        if tangan_kosong:
            smart_print(bot_memory, f"[{BOT_NAME}] ✨ UPGRADE SENJATA! Pakai [{best_inv_w_name}]!")
            return aksi_equip(best_inv_w_id)
        elif best_inv_w_score > equipped_w_score:
            smart_print(bot_memory, f"[{BOT_NAME}] ✨ UPGRADE SENJATA! Pakai [{best_inv_w_name}]!")
            return aksi_equip(best_inv_w_id)

    # 🔥 AUTO-CLEAN (SAPU JAGAT) DENGAN PENGECUALIAN BARANG UNIK 🔥
    skor_maksimal_kita = max(equipped_w_score, best_inv_w_score)
    for item in inventory:
        is_eq = isinstance(item, dict) and item.get("isEquipped", False)
        if not is_eq:
            i_id, i_name = ekstrak_info_item(item)
            if i_id in bot_memory["sampah_memory"]: continue 
            
            # Peta, Radio, Megaphone TIDAK AKAN PERNAH DIBUANG biar gak error server!
            if is_valid_weapon(i_name, item):
                skor_tas = get_weapon_score(i_name)
                if skor_tas < skor_maksimal_kita:
                    bot_memory["sampah_memory"].add(i_id) 
                    return aksi_buang(i_id, f"AUTO-CLEAN: Buang {i_name} usang!")

    # ================== PUNGUT BARANG ==================
    if len(barang_di_area) > 0:
        # 🔥 DARURAT SENJATA: Kalau tangan kosong, cari senjata dulu! 🔥
        if tangan_kosong:
            for b in barang_di_area:
                bid, bnm = ekstrak_info_item(b)
                if is_valid_weapon(bnm, b):
                    smart_print(bot_memory, f"[{BOT_NAME}] 🚨 DARURAT SENJATA! Sikat {bnm}!")
                    return aksi_pungut(b)

        # Kalau udah aman, looting normal
        for item_terbaik in barang_di_area:
            _, nama_barang = ekstrak_info_item(item_terbaik)
            nm_low = nama_barang.lower()
            
            # Cek limit 1 barang unit
            if "megaphone" in nm_low and punya_megaphone: continue
            if "radio" in nm_low and punya_radio: continue
            if "map" in nm_low and punya_map: continue
                
            tas_penuh = True if len(inventory) >= 10 else False
            is_koin = True if "moltz" in nm_low or "coin" in nm_low else False
            
            # Prioritas Vulture Koin
            if is_koin:
                smart_print(bot_memory, f"[{BOT_NAME}] 💰 MATA DUITAN! Ada {nama_barang}, SIKAT!")
                return aksi_pungut(item_terbaik)
            
            if not tas_penuh:
                smart_print(bot_memory, f"[{BOT_NAME}] 🎒 Ambil Barang: {nama_barang}!")
                return aksi_pungut(item_terbaik)

    # ================== CEK COOLDOWN ==================
    sisa_cd = bot_memory.get("group1_cd_end", 0) - time.time()
    if sisa_cd > 0: return {"type": "WAITING_CD"}

    # ================== SURVIVAL & HEALING DEWA ==================
    is_trapped_in_dz = False
    if is_death_zone_now or is_pending_dz_now:
        aksi_lari = aksi_move("🚨 ZONA MERAH/BAHAYA! Evakuasi Segera!")
        if aksi_lari: return aksi_lari
        else: is_trapped_in_dz = True

    # Heal diutamakan sebelum mikirin musuh
    batas_heal = 95 if is_trapped_in_dz else 80 
    if my_hp_val < batas_heal:
        if id_medical:
            smart_print(bot_memory, f"[{BOT_NAME}] 🏥 Pakai Medical Facility!")
            return aksi_interact(id_medical)
        elif id_bandage:
            smart_print(bot_memory, f"[{BOT_NAME}] 🚑 Suntik Obat! (HP:{my_hp_val})")
            return aksi_pakai_item(id_bandage)
        elif id_potion:
            smart_print(bot_memory, f"[{BOT_NAME}] 🚑 Minum Potion! (HP:{my_hp_val})")
            return aksi_pakai_item(id_potion)

    # 🔥 PROTOKOL KARTEL PEAXEL 🔥
    if jumlah_pengeroyok >= 3 and jumlah_pengeroyok > kekuatan_tim:
        aksi = aksi_move(f"🚨 Musuh {jumlah_pengeroyok} orang, geng kita cuma {kekuatan_tim}. KABURRR!")
        if aksi: return aksi
        else: smart_print(bot_memory, f"[{BOT_NAME}] 🛑 ZONA AKHIR BUNTU! TAWURAN SINI KAU!")

    if jumlah_pengeroyok >= 2 and jumlah_pengeroyok > kekuatan_tim and my_hp_val < 75:
        aksi = aksi_move(f"🚨 Kalah jumlah geng & HP Bocor! Mundur taktis dulu!")
        if aksi: return aksi

    # 🔥 SMART COMBAT LOGIC (NINJA ASSASSIN) 🔥
    if musuh_player_terlemah:
        target = musuh_player_terlemah
        hp_musuh = target.get("hp", 100)
        nama_musuh = target.get("name", "Player")
        jarak_musuh = target.get("jarak", 0)
        target_region = target.get("regionId")
        
        if tangan_kosong:
            aksi = aksi_move("Tangan kosong! Melarikan diri cari senjata...")
            if aksi: return aksi
            return aksi_serang(target.get("id"), "agent")

        if jarak_musuh == 0:
            if jumlah_teman > 0:
                smart_print(bot_memory, f"[{BOT_NAME}] 🤝 GANKING MAFIA! Bantu saudara hajar {nama_musuh}!")
                return aksi_serang(target.get("id"), "agent")
            elif hp_musuh <= 40:
                smart_print(bot_memory, f"[{BOT_NAME}] 🦅 VULTURE MODE! Nyampah kill {nama_musuh} (HP:{hp_musuh})!")
                return aksi_serang(target.get("id"), "agent")
            elif my_hp_val > 85 or hp_musuh <= my_hp_val:
                smart_print(bot_memory, f"[{BOT_NAME}] ⚔️ Eksekusi {nama_musuh} (HP:{hp_musuh})!")
                return aksi_serang(target.get("id"), "agent")
            else:
                aksi = aksi_move(f"⚠️ {nama_musuh} lebih sehat (HP:{hp_musuh}). Melipir ah, main aman!")
                if aksi: return aksi
                smart_print(bot_memory, f"[{BOT_NAME}] ⚔️ Mentok! Terpaksa duel mati-matian lawan {nama_musuh}!")
                return aksi_serang(target.get("id"), "agent")

        elif jarak_musuh > 0:
            if weapon_range > 0:
                smart_print(bot_memory, f"[{BOT_NAME}] 🎯 SNIPER! Tembak {nama_musuh} dari jauh!")
                return aksi_serang(target.get("id"), "agent")
            else:
                if hp_musuh <= 30 and my_hp_val > 70:
                    smart_print(bot_memory, f"[{BOT_NAME}] 🏃‍♂️ Kejar {nama_musuh} yg lagi sekarat!")
                    if str(target_region).lower() in bot_memory["visited_path"]: 
                        bot_memory["visited_path"].remove(str(target_region).lower())
                    bot_memory["visited_path"].append(str(target_region).lower())
                    return {"type": "move", "regionId": str(target_region).lower()}

    # 🔥 FARMING MONSTER AMAN 🔥
    if musuh_monster_terlemah:
        target = musuh_monster_terlemah
        nama_musuh = target.get("name", "Monster")
        jarak_musuh = target.get("jarak", 0)
        target_region = target.get("regionId")
        
        if not tangan_kosong and my_hp_val >= 80:
            if jarak_musuh > 0 and weapon_range == 0:
                smart_print(bot_memory, f"[{BOT_NAME}] 🏃‍♂️ Cari {nama_musuh} buat farming koin!")
                return {"type": "move", "regionId": str(target_region).lower()}
            else:
                smart_print(bot_memory, f"[{BOT_NAME}] 👹 Bantai {nama_musuh} buat Koin!")
                return aksi_serang(target.get("id"), "monster")

    if id_supply:
        smart_print(bot_memory, f"[{BOT_NAME}] 📦 Maling kotak Supply Cache!")
        return aksi_interact(id_supply)

    aksi_akhir = aksi_move("🕵️ Patroli cari duit & tempat aman...")
    if aksi_akhir: return aksi_akhir
        
    return {"type": "explore"}

# ================== RADAR & LAPORAN ==================
def print_live_status(state, game_id):
    self_data = state.get("self", {})
    region = state.get("currentRegion", {})
    
    hp = self_data.get('hp', '?')
    tas = len(self_data.get('inventory', []))
    loc = region.get('name', '?')
    
    senjata_info = "Tangan Kosong 👊"
    equipped_item = self_data.get("equippedWeapon") or self_data.get("weapon")
    
    if equipped_item:
        _, nm = ekstrak_info_item(equipped_item)
        if "fist" not in nm.lower() and "none" not in nm.lower(): 
            senjata_info = f"{nm} 🗡️"
            
    print(f"\n[🎮 GAME {game_id[-5:]}] [{BOT_NAME}] | HP:{hp} | Tas:{tas}/10 | Senj: {senjata_info} | Lokasi:{loc}")

def cetak_laporan_kemenangan(state):
    self_data = state.get("self", {})
    hp_akhir = self_data.get("hp", "?")
    inventory = self_data.get("inventory", [])
    
    print("\n" + "🏆"*25)
    print("  🎉🔥 CHAMPION! WINNER WINNER CHICKEN DINNER! 🔥🎉")
    print("🏆"*25)
    print(f"  👑 Sang Penguasa : {BOT_NAME.upper()}")
    print(f"  ❤️ Sisa HP       : {hp_akhir}/100")
    print(f"  🎒 Isi Tas       : {len(inventory)}/10 Barang")
    print("==================================================\n")

def cetak_laporan_forensik(bot_memory, current_state):
    print("\n" + "="*50)
    print(f"💀 LAPORAN FORENSIK KEMATIAN {BOT_NAME} 💀")
    print("="*50)
    
    state_sumber = current_state if isinstance(current_state, dict) else bot_memory.get("last_state", {})
    
    if not state_sumber:
        print("❓ Penyebab Kematian: Data menguap diculik server (Misterius).")
        print("="*50 + "\n")
        return
        
    self_data = state_sumber.get("self", {})
    region = state_sumber.get("currentRegion", {})
    alasan_resmi = False
    
    if "deathReason" in self_data:
        print(f"🔪 Alasan Resmi  : {self_data['deathReason']}")
        alasan_resmi = True
        
    if "killerName" in self_data or "killer" in self_data:
        print(f"🩸 Tersangka     : {self_data.get('killerName', self_data.get('killer', 'Unknown'))}")
        alasan_resmi = True
        
    print(f"\n🕵️ TKP : {region.get('name', '?')}")
    
    if not alasan_resmi:
        if region.get("isDeathZone", False): 
            print("⚠️ Kesimpulan Utama: 99% MATI KEPANGGANG BADAI DEATH ZONE! 🌪️🔥")
        else: 
            print("⚠️ Kesimpulan Utama: Gugur di medan perang.")
            
    print("="*50 + "\n")

# ================== MAIN LOOP ==================
def main():
    if API_KEY == "KOSONG" or API_KEY.startswith("ISI_"): 
        fatal(f"[{BOT_NAME}] API KEY kosong! Pastikan di-set di ecosystem.config.js!")
        
    game_id, agent_id = load_session()
    resume_berhasil = False
    
    if game_id and agent_id:
        print(f"🔄 [{get_waktu()}] [{BOT_NAME}] Sesi ditemukan! Coba RECONNECT ke game sebelumnya...")
        state = get_state(game_id, agent_id)
        
        if state and state != "MATI":
            is_alive = state.get("self", {}).get("isAlive", True)
            status_game = state.get("gameStatus", "").lower()
            
            if status_game not in ["finished", "cancelled"] and is_alive:
                print(f"✅ [{get_waktu()}] [{BOT_NAME}] RECONNECT BERHASIL! Melanjutkan pertempuran...")
                resume_berhasil = True
            else:
                print(f"⚠️ [{get_waktu()}] [{BOT_NAME}] Game lama sudah usai/Bot mati. Menghapus sesi...")
                clear_session()
        else:
            print(f"⚠️ [{get_waktu()}] [{BOT_NAME}] Room lama tidak valid/kadaluarsa. Menghapus sesi...")
            clear_session()
            
    # 🔥 PENCARI ROOM ANTI RATE-LIMIT 🔥
    if not resume_berhasil:
        agent_id = None
        game_id = None
        
        while not agent_id:
            game_id = get_waiting_game()
            
            if not game_id:
                delay = random.uniform(1.5, 3.5)
                print(f"🔄 [{BOT_NAME}] Re-scan radar dalam {delay:.1f} detik...\n")
                time.sleep(delay)
                continue
                
            agent_id = register_agent(game_id)
            
            if not agent_id:
                delay = random.uniform(1.0, 2.0)
                print(f"⏩ [{BOT_NAME}] Keduluan! Langsung tembak room lain ({delay:.1f}s)...\n")
                time.sleep(delay) 

        save_session(game_id, agent_id)
        start_game(game_id)
        
        print(f"⏳ [{get_waktu()}] [{BOT_NAME}] Menunggu game dimulai...")
        
        while True:
            state = get_state(game_id, agent_id)
            if state == "MATI":
                print(f"❌ [{BOT_NAME}] Game keburu dihapus/error sebelum mulai!")
                clear_session()
                sys.exit(1)
                
            if state and state.get("gameStatus", "").lower() not in ["waiting", "created", "pending", ""]:
                print(f"🔥 [{get_waktu()}] [{BOT_NAME}] GAME DIMULAI! MELEPAS BOT 🔥\n")
                break
                
            time.sleep(0.5) 

    bot_memory = {
        "visited_path": [], 
        "dz_memory": set(), 
        "pdz_memory": set(), 
        "taunted_agents": set(),
        "sampah_memory": set(), 
        "last_region_id": None, 
        "last_state": None, 
        "group1_cd_end": 0, 
        "last_print_time": 0, 
        "last_log_msg": ""
    }

    while True:
        try:
            state = get_state(game_id, agent_id)
            
            if state == "MATI":
                cetak_laporan_forensik(bot_memory, state)
                clear_session()
                break
                
            if not state:
                time.sleep(1)
                continue
                
            bot_memory["last_state"] = state
            
            if not state.get("self", {}).get("isAlive"):
                cetak_laporan_forensik(bot_memory, state)
                clear_session()
                break
                
            if state.get("gameStatus") == "finished":
                if state.get("self", {}).get("isAlive"): 
                    cetak_laporan_kemenangan(state)
                else: 
                    print(f"\n🏁 [{get_waktu()}] [{BOT_NAME}] MATCH SELESAI! GAMEOVER (Nyaris menang)!")
                clear_session()
                break
            
            if time.time() - bot_memory["last_print_time"] >= 20:
                print_live_status(state, game_id)
                bot_memory["last_print_time"] = time.time()
                bot_memory["last_log_msg"] = "" 

            action_payload = decide_action(state, bot_memory)
            
            if action_payload:
                if action_payload.get("type") == "WAITING_CD":
                    time.sleep(1.5)
                    continue
                    
                act_type = action_payload.get("type", "")
                res = send_action(game_id, agent_id, action_payload)
                
                if res and res.get("success"):
                    if act_type in ["pickup", "equip", "talk", "whisper", "drop"]: 
                        time.sleep(0.2) 
                    else: 
                        bot_memory["group1_cd_end"] = time.time() + TURN_DELAY
                        time.sleep(1) 
                else: 
                    if res and "error" in res:
                        err_msg = res.get("error", {}).get("message", "Error nggak jelas")
                        if "cooldown" not in err_msg.lower(): 
                            print(f"⚠️ [{BOT_NAME}] Server nolak aksi '{act_type}': {err_msg}")
                    time.sleep(1) 
            else: 
                time.sleep(1)
                
        except Exception:
            time.sleep(1)

if __name__ == "__main__":
    while True: 
        try:
            main()
        except Exception as e:
            print(f"💥 [{BOT_NAME}] Crash sistem: {e}. Reboot dalam 5 detik...")
            time.sleep(5)