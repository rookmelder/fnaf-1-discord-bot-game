import discord
from random import randint

class Game:
    def __init__(self, ctx, power, time, img, night):

        self.night_ai_presets = {
            1: [0, 0, 0, 0],
            2: [0, 3, 1, 1],
            3: [1, 0, 5, 2],
            4: [2, 2, 4, 6],
            5: [3, 5, 7, 5],
            6: [4, 10, 12, 16]
        }
        self.freddy = Freddy(self.night_ai_presets[night][0])
        self.bonnie = Bonnie(self.night_ai_presets[night][1])
        self.chica = Chica(self.night_ai_presets[night][2])
        self.foxy = Foxy(self.night_ai_presets[night][3])

        self.time = {"hours": 0, "seconds": 0, "nights": 1}
        self.start_time = None
        self.playing = True
        self.player = ctx
        self.img_message = img
        self.power_message = power
        self.time_message = time
        
        self.current_room = "desk"
        self.power = 999
        self.power_in_perc = 99
        self.consumption = 0
        self.elec = {
            "lights": [False, False],
            "doors": [False, False]
        }

    async def stop_game(self):
        self.playing = False
        await self.player.send('the game has ended. (type !stop)')
        return


    async def update_power(self):

        consumption = 0
        

        # night power
        intervals = {1: 9,2: 6, 3: 5, 4: 4, 5: 3, 6: 3}

        night = self.time["nights"]

        if self.time["seconds"] % intervals[night] == 0:
            self.power -= 1

        
        lights = self.elec["lights"]
        doors = self.elec["doors"]

        consumption += lights[0] + lights[1] + doors[0] + doors[1]
        if self.current_room != "desk":
            consumption += 1

        if consumption != self.consumption or self.power//10 != self.power_in_perc:
            await self.power_message.edit(content=f'{self.power//10}% || power: :zap:{":zap:" * consumption}')
            self.consumption = consumption
            self.power_in_perc = self.power//10
            

        self.power -= consumption


    async def logic_step(self):


        self.time["seconds"] += 1

        # we check if they're at the door and locked in (waiting for us to close the camera)
        if self.foxy.timer:
            self.foxy.timer -= 1
        if self.foxy.locked:
            self.foxy.locked -= 1
            if self.foxy.locked == 0:
                self.foxy.room = "desk"
                if self.current_room == "desk":
                    await self.jumpscare(self.foxy)
                    return
        if self.bonnie.locked:
            self.bonnie.locked -= 1
            if self.bonnie.locked == 0:
                await self.jumpscare(self.bonnie)
                return
        if self.chica.locked:
            self.chica.locked -= 1
            if self.chica.locked == 0:
                await self.jumpscare(self.chica)
                return

        await self.freddy_logic()

        # freddy has the change to move every 3 seconds
        if self.time["seconds"] % 3 == 0:

            if self.freddy.ready_to_move or self.freddy.countdown is not None:
                pass
            else:
                if self.current_room in ["desk"] or (self.current_room != "4b" and self.freddy.room == "4b"):
                    if randint(1, 20) <= self.freddy.ai_level:
                        countdown = {1: 15, 2: 13, 3: 11, 4: 9, 5: 7, 6: 5, 7: 3, 8: 2, 9: 1}
                        self.freddy.countdown = countdown.get(self.freddy.ai_level) if self.freddy.ai_level <= 9 else 1


        # every 5 seconds, chance to move
        if self.time["seconds"] % 5 == 0:
            if randint(1, 20) <= self.bonnie.ai_level:
                await self.bonnie_logic()
            if randint(1, 20) <= self.chica.ai_level:
                await self.chica_logic()
            if randint(1, 20) <= self.foxy.ai_level:
                await self.foxy_logic()

        # power usage
        await self.update_power()

        # check time
        if self.time["seconds"] % 86 == 0:  # 86
            self.time["hours"] += 1
            await self.time_message.edit(content=f'{self.time["hours"]}am')

            if 2 <= self.time["hours"] <= 4:  # game updates ai level at 2, 3 and 4am
                self.bonnie.ai_level += 1
                if self.time["hours"] > 2:
                    self.chica.ai_level += 1
                    self.foxy.ai_level += 1

            # if it's 6am
            if self.time["hours"] == 6:
                await self.player.send(f'congrats you survived the night!')
                await self.stop_game()
                return



    async def draw(self):
        room = self.current_room
        temp = f'{room}_'

        if room.lower() == "desk":

            if self.elec["lights"][0] and not self.elec["doors"][0] and self.bonnie.room == "desk":
                temp += "b"
            if self.elec["lights"][0]:
                temp += "ll"
            if self.elec["doors"][0]:
                temp += "ld"
            
            if self.elec["lights"][1] and self.chica.room == "desk":
                temp += "c"
            if self.elec["lights"][1]:
                temp += "rl"
            if self.elec["doors"][1]:
                temp += "rd"
            await self.img_message.edit(attachments=[discord.File(open(f'./pics/{temp.lower()}.png', "rb"), "image.jpg")])
            return



        if self.freddy.room == room:
            temp += "f"
        if self.bonnie.room == room:
            temp += "b"
        if self.chica.room == room:
            temp += "c"
        if self.foxy.room == room:
            temp += "x"
            if room == "1c":
                temp += f'{self.foxy.stage}'
            if room == "2a":
                await self.img_message.edit(attachments=[discord.File(open(f'./pics/{self.foxy.running}', "rb"), "image.gif")])
                self.foxy.room = "desk"
                return

        
        await self.img_message.edit(attachments=[discord.File(open(f'./pics/cam_{temp.lower()}.png', "rb"), "image.jpg")])


    async def freddy_logic(self):
        """
        Whenever Freddy gets a successful movement opportunity, he doesn't immediately move.
        Freddy starts a countdown. When it hits 0 he moves to the next room in his path. Unless you are looking at the cameras. Then he waits till you look away.
        """

        freddy = self.freddy

        if freddy.countdown is not None:
            freddy.countdown -= 1
            if freddy.countdown != 0:
                return
            freddy.ready_to_move = True
            freddy.countdown = None
        
        if freddy.ready_to_move:

            if freddy.room == "4b" and self.current_room not in ["4b", "desk"]:
                if not self.elec["doors"][1]:
                    freddy.room = "desk"
                    freddy.ready_to_move = False
                    freddy.countdown = None
                    return
                else:
                    freddy.ready_to_move = False
                    freddy.countdown = None
                    freddy.room = None # we make him disappear
                    return

            if freddy.room not in ["4b", "desk"] and self.current_room == "desk":
                freddy.room_index += 1
                freddy.room = freddy.path[freddy.room_index]
                freddy.ready_to_move = False
                freddy.countdown = None
                return
        


    async def bonnie_logic(self):
        bonnie = self.bonnie
        was_in_cam = False
        index = bonnie.path.index(bonnie.room)
        path = bonnie.path

        if self.current_room == bonnie.room:
            was_in_cam = True

        if index == len(path) - 1:
            if self.elec["doors"][0]:
                # If the left door is closed, Bonnie returns to a previous room
                bonnie.room = path[3] if isinstance(path[3], str) else path[3][0]
            else:
                bonnie.locked = 25
                return
        else:
            possible_next_rooms = path[index + 1]
            if isinstance(possible_next_rooms, str):
                bonnie.room = possible_next_rooms
            else:
                next_room = randint(0, len(possible_next_rooms) - 1)
                bonnie.room = possible_next_rooms[next_room]

        if was_in_cam or self.current_room == bonnie.room:
            await self.draw()
    

    async def chica_logic(self):
        chica = self.chica
        was_in_cam = False
        index = chica.path.index(chica.room)
        path = chica.path

        if self.current_room == chica.room:
            was_in_cam = True

        if index == len(path) - 1:
            if self.elec["doors"][1]:
                # If the right door is closed, Chica returns to a previous room
                chica.room = path[3] if isinstance(path[3], str) else path[3][0]
            else:
                chica.locked = 25
                return
        else:
            possible_next_rooms = path[index + 1]
            if isinstance(possible_next_rooms, str):
                chica.room = possible_next_rooms
            else:
                next_room = randint(0, len(possible_next_rooms) - 1)
                chica.room = possible_next_rooms[next_room]

        if was_in_cam or self.current_room == chica.room:
            await self.draw()
    

    async def foxy_logic(self):
            foxy = self.foxy

            if self.current_room == "desk" and not foxy.timer and not foxy.locked:
                foxy.stage += 1
                if foxy.stage == 4:
                    foxy.room = "2a"
                    foxy.locked = 25
                    return



    async def jumpscare(self, anim):
        await self.img_message.edit(attachments=[discord.File(open(f'./pics/{anim.jumpscare}', "rb"), "gif.gif")])
        await self.stop_game()


class Animatronic:
    def __init__(self, ai_level):
        self.ai_level = ai_level


class Freddy(Animatronic):
    def __init__(self, ai_level=0):
        super().__init__(ai_level)
        self.name = "freddy"
        self.room = "1a"
        self.room_index = 0
        self.path = ["1a", "1b", "7", "6", "4a", "4b", "desk"]
        self.jumpscare = "freddy_jumpscare.gif"
        self.locked = None
        self.countdown = None
        self.ready_to_move = False


    

class Bonnie(Animatronic):
    def __init__(self, ai_level=0):
        super().__init__(ai_level)
        self.name = "bonnie"
        self.room = "1a"
        self.path = ["1a", ["1b", "5"], "1b", ["5", "2a"], "5", ["1b", "2a"], "2a", ["3", "2b"], "3", ["2a", "2b","desk"], "2b", ["3", "desk"], "desk"]
        self.jumpscare = "bonnie_jumpscare.gif"
        self.locked = None
    
    

class Chica(Animatronic):
    def __init__(self, ai_level=0):
        super().__init__(ai_level)
        self.name = "chica"
        self.room = "1a"
        self.path = ["1a", ["1b"], "1b", ["7", "6", "4a"], "7", ["6", "4a"], "6", ["7", "4a"], "4a", ["1b", "4b"], "4b", ["4a", "desk"], "desk"]
        self.jumpscare = "chica_jumpscare.gif"
        self.locked = None

class Foxy(Animatronic):
    def __init__(self, ai_level=0):
        super().__init__(ai_level)
        self.name = "foxy"
        self.room = "1c"
        self.jumpscare = "foxy_jumpscare.gif"
        self.stage = 1
        self.times_out = 0
        self.timer = 0
        self.running = "foxy_running.gif"
        self.locked = None
