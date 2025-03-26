from django.db import models

# Create your models here.

class Game(models.Model):
    room_name = models.CharField(max_length=50, unique=True)
    player1_name = models.CharField(max_length=50)
    player2_name = models.CharField(max_length=50, null=True, blank=True)
    current_turn = models.CharField(max_length=50, null=True, blank=True)
    board = models.CharField(max_length=9, default='---------')  # - for empty, X for player1, O for player2
    winner = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    player1_score = models.IntegerField(default=0)
    player2_score = models.IntegerField(default=0)
    rematch_player1 = models.BooleanField(default=False)
    rematch_player2 = models.BooleanField(default=False)

    def __str__(self):
        return f"Game {self.room_name}"

    def reset_for_rematch(self):
        self.board = '-' * 9
        self.is_active = True
        self.winner = None
        self.rematch_player1 = False
        self.rematch_player2 = False
        # Alternate who starts in rematches
        self.current_turn = self.player2_name if self.current_turn == self.player1_name else self.player1_name
        self.save()
