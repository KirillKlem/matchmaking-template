import logging
from flask import Flask, request, jsonify, current_app
import json
import os
from collections import defaultdict
import random

app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/ping', methods=['GET'])
def send():
    return "pong!"

@app.get('/matchmaking/users')
def get_waiting_users():
    test_name = request.args.get('test_name')
    epoch = request.args.get('epoch')

    if test_name is None or epoch is None:
        return jsonify({"error": "Missing parameters"}), 400

    file_path = os.path.join(current_app.root_path, "tests", test_name, f"{epoch}.json")

    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
            return jsonify(data)
    else:
        return jsonify({"error": "File not found"}), 404

@app.route('/matchmaking/match', methods=['POST'])
def log_match():
    test_name = request.args.get('test_name')
    epoch = request.args.get('epoch')

    if test_name is None or epoch is None:
        return jsonify({"error": "Missing parameters"}), 400

    file_path = os.path.join(current_app.root_path, "tests", test_name, f"test.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            epoches = json.load(file)

    new_epoch = epoches.get(epoch)

    data = request.get_json()
    logger.info(data)
    return jsonify({"epoch": new_epoch, "test_name": test_name}), 200

def calculate_team_metrics(team):
    mmr_sum = sum(player['mmr'] for player in team)
    if team:
        mmr_avg = mmr_sum / len(team)
        mmr_diff = max(player['mmr'] for player in team) - min(player['mmr'] for player in team)
    else:
        mmr_avg = 0
        mmr_diff = 10**6
    return mmr_avg, mmr_diff

def add_player_to_team(team, player, role):
    team.append({**player, "current_role": role})
    return calculate_team_metrics(team)

def find_best_team_assignment(role_buckets, used_players, role, red_team, blue_team):
    first_player = next((player for player in role_buckets[role] if player["id"] not in used_players), None)
    second_player = next((player for player in role_buckets[role] if player["id"] not in used_players and player['id'] != first_player['id']), None)
    if not first_player and not second_player:
        return None

    best_choice = None

    red_team_with_first = red_team.copy()
    blue_team_with_second = blue_team.copy()

    if first_player and second_player:
        both_players_flag = True 

        red_avg1, red_diff1 = add_player_to_team(red_team_with_first, first_player, role)
        blue_avg1, blue_diff1 = add_player_to_team(blue_team_with_second, second_player, role)

        red_team_with_second = red_team.copy()
        blue_team_with_first = blue_team.copy()
        red_avg2, red_diff2 = add_player_to_team(red_team_with_second, second_player, role)
        blue_avg2, blue_diff2 = add_player_to_team(blue_team_with_first, first_player, role)

        metric_diff1 = abs(red_avg1 - blue_avg1) + red_diff1 + blue_diff1
        metric_diff2 = abs(red_avg2 - blue_avg2) + red_diff2 + blue_diff2

    else:
        both_players_flag = False 

        red_avg1, red_diff1 = add_player_to_team(red_team_with_first, first_player, role)
        blue_avg1, blue_diff1 = calculate_team_metrics(blue_team)

        blue_team_with_first = blue_team.copy()
        red_avg2, red_diff2 = calculate_team_metrics(red_team)
        blue_avg2, blue_diff2 = add_player_to_team(blue_team_with_first, first_player, role)

        metric_diff1 = abs(red_avg1 - blue_avg1) + red_diff1 + blue_diff1
        metric_diff2 = abs(red_avg2 - blue_avg2) + red_diff2 + blue_diff2

    if metric_diff1 <= metric_diff2:
        best_choice = (first_player, second_player, 'red_first', both_players_flag)

    else:
        best_choice = (first_player, second_player, 'blue_first', both_players_flag)

    return best_choice

def create_match(waiting_users):
    # Сортируем игроков по времени ожидания (от большего к меньшему)
    waiting_users.sort(key=lambda user: user["waitingTime"], reverse=True)
    role_buckets = defaultdict(list)
    for user in waiting_users:
        for role in user["roles"]:
            role_buckets[role].append(user)

    red_team = []
    blue_team = []
    used_players = set()

    roles = ["top", "mid", "bot", "sup", "jungle"]
    random.shuffle(roles)
    for role in roles:
        choice = find_best_team_assignment(role_buckets, used_players, role, red_team, blue_team)
        
        if not choice:
            continue
        
        first_player, second_player, assignment, both_players_flag = choice

        if assignment == 'red_first':
            red_team.append({**first_player, "current_role": role})
            if both_players_flag:
                blue_team.append({**second_player, "current_role": role})
        else:
            blue_team.append({**first_player, "current_role": role})
            if both_players_flag:
                red_team.append({**second_player, "current_role": role})

        used_players.add(first_player['id'])
        if both_players_flag:
            used_players.add(second_player['id'])

    return {"red": red_team, "blue": blue_team}

@app.route('/matchmaking/create_match', methods=['POST'])
def create_match_endpoint():
    data = request.get_json()
    test_name = data.get("test_name")
    epoch = data.get("epoch")
    waiting_users = data.get("users")

    if not test_name or not epoch or not waiting_users:
        return jsonify({"error": "Missing parameters"}), 400
    
    print(waiting_users)
    match = create_match(waiting_users)
    match_result = {
        "test_name": test_name,
        "last_epoch_id": epoch,
        "match": [
            {
                "side": "red",
                "user": match["red"]
            },
            {
                "side": "blue",
                "user": match["blue"]
            }
        ]
    }
    print(match_result)
    return jsonify(match_result), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
