from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db import models
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from .models import Game

def home(request):
    # Store player name in session if provided
    if request.method == 'POST':
        player_name = request.POST.get('player_name')
        if player_name:
            request.session['player_name'] = player_name
            return redirect('home')

    player_name = request.session.get('player_name')
    if not player_name:
        return render(request, 'game/enter_name.html')

    # Show available rooms and active games
    my_games = Game.objects.filter(
        models.Q(player1_name=player_name) | models.Q(player2_name=player_name),
        is_active=True
    )
    available_rooms = Game.objects.filter(player2_name__isnull=True, is_active=True).exclude(player1_name=player_name)
    
    return render(request, 'game/home.html', {
        'player_name': player_name,
        'my_games': my_games,
        'available_rooms': available_rooms
    })

def new_game(request):
    player_name = request.session.get('player_name')
    if not player_name:
        return redirect('home')

    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        if Game.objects.filter(room_name=room_name).exists():
            return render(request, 'game/new_game.html', {'error': 'Room name already exists'})
        
        game = Game.objects.create(
            room_name=room_name,
            player1_name=player_name,
            current_turn=player_name
        )
        return redirect('game_detail', game_id=game.id)
    return render(request, 'game/new_game.html')

def join_game(request, game_id):
    player_name = request.session.get('player_name')
    if not player_name:
        # Store the game ID in session for redirect after name entry
        request.session['pending_game_id'] = game_id
        return redirect('enter_name')

    game = get_object_or_404(Game, id=game_id)
    if game.player2_name is None and game.player1_name != player_name:
        game.player2_name = player_name
        game.current_turn = game.player1_name  # First player starts
        game.save()
        return redirect('game_detail', game_id=game.id)
    elif game.player1_name == player_name or game.player2_name == player_name:
        return redirect('game_detail', game_id=game.id)
    return redirect('home')

def enter_name(request):
    if request.method == 'POST':
        player_name = request.POST.get('player_name')
        if player_name:
            request.session['player_name'] = player_name
            # Check if there's a pending game to join
            pending_game_id = request.session.pop('pending_game_id', None)
            if pending_game_id:
                return redirect('join_game', game_id=pending_game_id)
            return redirect('home')
    return render(request, 'game/enter_name.html')

def game_detail(request, game_id):
    player_name = request.session.get('player_name')
    if not player_name:
        request.session['pending_game_id'] = game_id
        return redirect('enter_name')

    game = get_object_or_404(Game, id=game_id)
    if player_name not in [game.player1_name, game.player2_name] and game.player2_name is not None:
        return redirect('home')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'board': game.board,
            'current_turn': game.current_turn,
            'is_active': game.is_active,
            'winner': game.winner,
            'player_symbol': 'X' if player_name == game.player1_name else 'O',
            'status_message': get_status_message(game, player_name),
            'player2_joined': game.player2_name is not None,
            'is_host': player_name == game.player1_name,
            'share_url': request.build_absolute_uri(reverse('join_game', args=[game.id])),
            'player1_score': game.player1_score,
            'player2_score': game.player2_score,
            'rematch_player1': game.rematch_player1,
            'rematch_player2': game.rematch_player2,
            'player1_name': game.player1_name,
            'player2_name': game.player2_name
        })
    
    share_url = request.build_absolute_uri(reverse('join_game', args=[game.id]))
    return render(request, 'game/game_detail.html', {
        'game': game,
        'player_name': player_name,
        'is_host': player_name == game.player1_name,
        'share_url': share_url
    })

@require_http_methods(["POST"])
def delete_game(request, game_id):
    player_name = request.session.get('player_name')
    if not player_name:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
        
    game = get_object_or_404(Game, id=game_id)
    if game.player1_name != player_name:
        return JsonResponse({'error': 'Not authorized'}, status=403)
        
    game.delete()
    return JsonResponse({'status': 'success', 'message': 'Game deleted successfully'})

def get_status_message(game, player_name):
    if not game.is_active:
        if game.winner:
            if game.winner == player_name:
                return 'You won! 🎉'
            return f'{game.winner} won!'
        return 'Game ended in a draw!'
    else:
        if game.current_turn == player_name:
            return 'Your turn'
        return f"{game.current_turn}'s turn"

@require_http_methods(["POST"])
def make_move(request, game_id):
    player_name = request.session.get('player_name')
    if not player_name:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
        
    game = get_object_or_404(Game, id=game_id)
    if game.current_turn != player_name or not game.is_active:
        return JsonResponse({'error': 'Invalid move'}, status=400)
        
    try:
        position = int(request.POST.get('position', ''))
        if not (0 <= position <= 8) or game.board[position] != '-':
            return JsonResponse({'error': 'Invalid move'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid position'}, status=400)
        
    board_list = list(game.board)
    symbol = 'X' if player_name == game.player1_name else 'O'
    board_list[position] = symbol
    game.board = ''.join(board_list)
    
    # Check for win
    win_combinations = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
        [0, 4, 8], [2, 4, 6]  # Diagonals
    ]
    
    for combo in win_combinations:
        if all(board_list[i] == symbol for i in combo):
            game.winner = player_name
            game.is_active = False
            # Update score
            if player_name == game.player1_name:
                game.player1_score += 1
            else:
                game.player2_score += 1
            game.save()
            return JsonResponse({
                'status': 'win',
                'board': game.board,
                'status_message': get_status_message(game, player_name),
                'player1_score': game.player1_score,
                'player2_score': game.player2_score
            })
    
    # Check for draw
    if '-' not in board_list:
        game.is_active = False
        game.save()
        return JsonResponse({
            'status': 'draw',
            'board': game.board,
            'status_message': get_status_message(game, player_name),
            'player1_score': game.player1_score,
            'player2_score': game.player2_score
        })
    
    # Game continues
    game.current_turn = game.player2_name if player_name == game.player1_name else game.player1_name
    game.save()
    
    return JsonResponse({
        'status': 'continue',
        'board': game.board,
        'status_message': get_status_message(game, player_name),
        'player1_score': game.player1_score,
        'player2_score': game.player2_score
    })

@require_http_methods(["POST"])
def request_rematch(request, game_id):
    player_name = request.session.get('player_name')
    if not player_name:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
        
    game = get_object_or_404(Game, id=game_id)
    if player_name not in [game.player1_name, game.player2_name]:
        return JsonResponse({'error': 'Not a player in this game'}, status=403)
        
    # Set rematch flag for the requesting player
    if player_name == game.player1_name:
        game.rematch_player1 = True
    else:
        game.rematch_player2 = True
    
    # If both players want rematch, reset the game
    if game.rematch_player1 and game.rematch_player2:
        game.reset_for_rematch()
        
    game.save()
    
    return JsonResponse({
        'status': 'success',
        'rematch_player1': game.rematch_player1,
        'rematch_player2': game.rematch_player2,
        'board': game.board,
        'is_active': game.is_active,
        'current_turn': game.current_turn,
        'player1_score': game.player1_score,
        'player2_score': game.player2_score
    })
