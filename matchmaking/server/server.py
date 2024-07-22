import logging
from flask import Flask, request, jsonify, current_app
import json
import os
from collections import defaultdict

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

def create_match(waiting_users):
    # Сортируем игроков по времени ожидания (от большего к меньшему)
    waiting_users.sort(key=lambda user: user["waitingTime"], reverse=True)
    role_buckets = defaultdict(list)
    for user in waiting_users:
        for role in user["roles"]:
            role_buckets[role].append(user)

    teams = {"red": [], "blue": []}
    used_players = set()
    red_team_mmr = 0
    blue_team_mmr = 0

    for role in ["top", "mid", "bot", "sup", "jungle"]:
        first_player = next((player for player in role_buckets[role] if player["id"] not in used_players), None)
        second_player = next((player for player in role_buckets[role] if player["id"] not in used_players and player != first_player), None)

        if first_player and second_player:
            if red_team_mmr <= blue_team_mmr:
                teams["red"].append({**first_player, "current_role": role})
                used_players.add(first_player["id"])
                red_team_mmr += first_player["mmr"]

                teams["blue"].append({**second_player, "current_role": role})
                used_players.add(second_player["id"])
                blue_team_mmr += second_player["mmr"]
            else:
                teams["blue"].append({**first_player, "current_role": role})
                used_players.add(first_player["id"])
                blue_team_mmr += first_player["mmr"]

                teams["red"].append({**second_player, "current_role": role})
                used_players.add(second_player["id"])
                red_team_mmr += second_player["mmr"]

        elif first_player:
            if red_team_mmr <= blue_team_mmr:
                teams["red"].append({**first_player, "current_role": role})
                used_players.add(first_player["id"])
                red_team_mmr += first_player["mmr"]
            else:
                teams["blue"].append({**first_player, "current_role": role})
                used_players.add(first_player["id"])
                blue_team_mmr += first_player["mmr"]

        elif second_player:
            if red_team_mmr <= blue_team_mmr:
                teams["red"].append({**second_player, "current_role": role})
                used_players.add(second_player["id"])
                red_team_mmr += second_player["mmr"]
            else:
                teams["blue"].append({**second_player, "current_role": role})
                used_players.add(second_player["id"])
                blue_team_mmr += second_player["mmr"]

    return teams

@app.route('/matchmaking/create_match', methods=['POST'])
def create_match_endpoint():
    data = request.get_json()
    test_name = data.get("test_name")
    epoch = data.get("epoch")
    waiting_users = data.get("users")

    if not test_name or not epoch or not waiting_users:
        return jsonify({"error": "Missing parameters"}), 400

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

    return jsonify(match_result), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
