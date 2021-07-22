import time
import random
from otree.api import *

from .images import generate_image, encode_image


doc = """
Experimental colors game
"""


class Constants(BaseConstants):
    name_in_url = "colors"
    players_per_group = None
    num_rounds = 1
    game_duration = 1

    colors = ["red", "green", "blue", "yellow", "magenta", "cyan"]
    color_values = {  # RRGGBB hexcodes
        "red": "#FF0000",
        "green": "#00FF00",
        "blue": "#0000FF",
        "yellow": "#FFFF00",
        "magenta": "#FF00FF",
        "cyan": "#00FFFF",
    }
    color_keys = {
        "r": "red",
        "g": "green",
        "b": "blue",
        "y": "yellow",
        "m": "magenta",
        "c": "cyan",
    }


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    total_puzzles = models.IntegerField(initial=0)
    total_solved = models.IntegerField(initial=0)


# puzzle-specific stuff


def generate_puzzle(player: Player):
    color = random.choice(Constants.colors)
    text = random.choice(Constants.colors)
    return color, text


class Trial(ExtraModel):
    """A model to keep record of all generated puzzles"""

    player = models.Link(Player)

    timestamp = models.FloatField(initial=0)
    iteration = models.IntegerField(initial=0)

    color = models.StringField()
    text = models.StringField()
    congruent = models.BooleanField()

    # the following fields remain null for unanswered trials
    answer = models.StringField()
    is_correct = models.BooleanField()


def play_game(player: Player, data: dict):
    """Handles iterations of the game on a live page

    Messages:
    - server < client {'next': true} -- request for next (or first) puzzle
    - server > client {'image': data} -- puzzle image
    - server < client {'answer': data} -- answer to a puzzle
    - server > client {'feedback': true|false|null} -- feedback on the answer (null for empty answer)
    """

    # get last trial, if any
    trials = Trial.filter(player=player)
    trial = trials[-1] if len(trials) else None
    iteration = trial.iteration if trial else 0

    # generate and return first or next puzzle
    if "next" in data:

        color, text = generate_puzzle(player)
        Trial.create(
            player=player,
            timestamp=time.time(),
            iteration=iteration + 1,
            color=color,
            text=text,
        )

        image = generate_image(text, Constants.color_values[color])
        data = encode_image(image)
        return {player.id_in_group: {"image": data}}

    # check given answer and return feedback
    if "answer" in data:
        answer = data["answer"]

        if answer != "":
            trial.answer = answer
            trial.is_correct = answer == trial.color

        return {player.id_in_group: {'feedback': trial.is_correct}}

    # otherwise
    raise ValueError("Invalid message from client!")


def custom_export(players):
    """Dumps all the puzzles generated"""
    yield [
        "session",
        "participant_code",
        "time",
        "iteration",
        "text",
        "color",
        "congruent",
        "answer",
        "is_correct",
    ]
    for p in players:
        participant = p.participant
        session = p.session
        for z in Trial.filter(player=p):
            yield [
                session.code,
                participant.code,
                z.timestamp,
                z.iteration,
                z.text,
                z.color,
                z.congruent,
                z.answer,
                z.is_correct,
            ]


# PAGES


class Intro(Page):
    pass


class Game(Page):
    timeout_seconds = Constants.game_duration * 60
    live_method = play_game

    @staticmethod
    def js_vars(player: Player):
        return dict(color_keys=Constants.color_keys, delay=1000, allow_skip=False)


class Results(Page):
    pass


page_sequence = [Intro, Game, Results]
