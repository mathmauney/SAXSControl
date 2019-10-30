import tkinter as tk
import math
import logging

logger = logging.getLogger('python')


class FlowPath(tk.Canvas):
    class Valve:
        def __init__(self, canvas, x, y, name, angle_off=0):
            self.x = x
            self.y = y
            self.name = name
            self.angle_off = math.radians(angle_off)
            self.big_radius = 100 * canvas.valve_scale
            self.small_radius = 20 * canvas.valve_scale
            self.offset = 60 * canvas.valve_scale
            self.arc_radius = self.offset + self.small_radius
            self.position = -1
            self.rads = math.radians(60)
            self.canvas = canvas
            self.big_circle = canvas.create_circle(x, y, self.big_radius, fill='dimgray', outline='dimgray', tag=self.name)
            self.center_circle = canvas.create_circle(x, y, self.small_radius, fill='dimgray', outline='dimgray', tag=self.name)
            self.circles = []
            self.fluid_lines = []
            self.connected_valves = []
            self.propagation = [False, False, False, False, False, False]
            self.hardware = None
            for i in range(0, 6):
                circle = canvas.create_circle(x+self.offset*math.cos(i*self.rads+self.angle_off), y+self.offset*math.sin(i*self.rads+self.angle_off), self.small_radius, fill='white', outline='white', tag=self.name)
                self.circles.append(circle)
                self.fluid_lines.append([])
                self.connected_valves.append([])
            self.fluid_lines.append([])  # for center circle
            self.connected_valves.append([])

        def connect(self, object_, position):
            """Link a line to an in or out port of the valve."""
            if position == 'center':
                position = 6
            if isinstance(object_, tuple):
                self.connected_valves[position].append(object_)
            else:
                self.fluid_lines[position].append(object_)   # TODO: Add way to associate real valve to diagram

        def assign_to_hardware(self):
            """Spawn a popup that allows the valve graphic to be associated with a hardware valve."""
            def set_choice(self, selected):
                choice_index = options.index(selected)
                self.hardware = self.canvas.window.instruments[choice_index]
                win.destroy()
            win = tk.Toplevel()
            win.wm_title("Valve Assignment")
            label = tk.Label(win, text='Select hardware:')
            label.grid(row=0, column=0, columnspan=2)
            options = []
            if len(self.canvas.window.instruments) > 0:
                for i in range(0, len(self.canvas.window.instruments)):
                    options.append(self.canvas.window.instruments[i].name)
                selection = tk.StringVar(options[0])
                menu = tk.OptionMenu(win, selection, *options)
                menu.grid(row=1, column=0, columnspan=2)
                ok_button = tk.Button(win, text="Unlock", command=lambda: set_choice(selection.get()))
                ok_button.grid(row=2, column=0)
            else:
                tk.Label(win, text='No hardware found.').grid(row=1, column=0, columnspan=2)
            cancel_button = tk.Button(win, text="Cancel", command=win.destroy)
            cancel_button.grid(row=2, column=1)

        def propagate_fluid(self, port, fluid_color):
            pass

    class SelectionValve(Valve):
        def __init__(self, canvas, x, y, name, angle_off=0):
            super().__init__(canvas, x, y, name, angle_off)
            self.canvas.itemconfig(self.center_circle, fill='white', outline='white', tag=self.name)
            self.color = 'black'
            self.colors = [None, None, None, None, None, None]
            self.gui_names = ['', '', '', '', '', '']   # 0 is rightmost, goes clockwise
            self.hardware_names = ['', '', '', '', '', '']
            self.propagation.append(False)
            for i in range(0, 6):
                self.canvas.itemconfig(self.circles[i], tag=self.name+str(i))
                self.canvas.tag_bind(self.name+str(i), '<Button-1>', lambda event, num=i: self.set_manual_position(self.gui_names[num]))

        def set_position(self, position_in, color=None):
            """Set the valve position to one of the 6 outputs on the gui."""
            if type(position_in) is str:
                if position_in == '':
                    return
                position = self.gui_names.index(position_in)
            elif position_in in range(0, 6):
                position = position_in
            else:
                raise ValueError('Invalid Position, ' + str(position_in))
            if color is not None:
                self.color = color
            elif self.colors[position] is not None:
                self.color = self.colors[position]
            self.canvas.itemconfig(self.circles[position], fill='white', outline='white')
            self.canvas.itemconfig(self.center_circle, fill=self.color, outline=self.color)
            self.canvas.itemconfig(self.circles[position], fill=self.color, outline=self.color)
            try:
                self.canvas.delete(self.channel)
            except AttributeError:
                pass
            self.channel = self.canvas.create_polygon([self.x+self.small_radius*math.sin(position*self.rads+self.angle_off), self.y-self.small_radius*math.cos(position*self.rads+self.angle_off),
                                                       self.x+self.offset*math.cos(position*self.rads+self.angle_off)+self.small_radius*math.sin(position*self.rads+self.angle_off), self.y+self.offset*math.sin(position*self.rads+self.angle_off)-self.small_radius*math.cos(position*self.rads+self.angle_off),
                                                       self.x+self.offset*math.cos(position*self.rads+self.angle_off)-self.small_radius*math.sin(position*self.rads+self.angle_off), self.y+self.offset*math.sin(position*self.rads+self.angle_off)+self.small_radius*math.cos(position*self.rads+self.angle_off),
                                                       self.x-self.small_radius*math.sin(position*self.rads+self.angle_off), self.y+self.small_radius*math.cos(position*self.rads+self.angle_off)],
                                                      fill=self.color, outline=self.color)
            if position != self.position:
                self.position = position
                for i in range(0, 6):
                    self.canvas.tag_raise(self.circles[i])
                if self.propagation[position] is True:
                    self.propagate_fluid(position, self.color)
                if self.propagation[6] is True:
                    self.propagate_fluid(6, self.color)

        def set_manual_position(self, position):    # TODO: Add in actual valve switching
            """Change the valve position after being clicked both visually and physically."""
            if self.canvas.window.instruments is None:
                self.set_position(position)
            elif self.hardware is None:
                self.assign_to_hardware()
            elif self.canvas.is_unlocked and position is not '':
                hardware_pos = self.hardware_names.index(position)+1
                self.hardware.switchvalve(hardware_pos)
                self.position = position

        def set_auto_position(self, position):    # TODO: Add in actual valve switching
            """Change the valve position after being clicked both visually and physically."""
            if self.hardware is None:
                raise ValueError
            elif position is not '':
                hardware_pos = self.hardware_names.index(position)+1
                self.hardware.switchvalve(hardware_pos)
                self.position = position

        def name_position(self, position, name):
            """Define the name for a hardware port position."""
            if position > 6 or position < 0:
                raise ValueError('Position out of Range')
            elif type(name) is not str:
                raise ValueError('Position names must be strings.')
            elif name == '':
                pass
            elif name not in self.gui_names:
                raise ValueError(str(name) + ' not in known valve names: ' + str(self.gui_names))
            self.hardware_names[position] = name

        def propagate_fluid(self, port, fluid_color):
            if isinstance(self.position, str):
                position = self.gui_names.index(self.position)
            else:
                position = self.position
            if port == 'center':
                port = 6
            if self.position == port:
                self.set_position(port, fluid_color)
                for line in self.fluid_lines[6]:
                    self.canvas.itemconfig(line, fill=self.color, outline=self.color)
                for (valve, port2) in self.connected_valves[6]:
                    valve.propagate_fluid(port2, fluid_color)
            elif port == 6:
                self.set_position(self.position, fluid_color)
                for line in self.fluid_lines[position]:
                    self.canvas.itemconfig(line, fill=self.color, outline=self.color)
                for (valve, port2) in self.connected_valves[position]:
                    valve.propagate_fluid(port2, fluid_color)

    class SampleValve(Valve):
        def __init__(self, canvas, x, y, name, angle_off=0):
            super().__init__(canvas, x, y, name, angle_off)
            self.inner_circle = self.canvas.create_circle(x, y, self.offset-self.small_radius, fill='dimgray', outline='dimgray', tag=self.name)
            self.right_color = 'grey30'
            self.left_color = 'grey30'
            self.canvas.tag_bind(name, '<Button-1>', lambda event: self.set_manual_position(self.position+1))

        def set_position(self, position, **kwargs):
            self.left_color = kwargs.pop('left_color', self.left_color)
            self.right_color = kwargs.pop('right_color', self.right_color)
            prev_position = self.position
            self.position = position % 2
            try:
                self.canvas.delete(self.arc1)
                self.canvas.delete(self.arc2)
            except AttributeError:
                pass
            self.canvas.itemconfig(self.circles[0], fill=self.right_color, outline=self.right_color)
            self.canvas.itemconfig(self.circles[3], fill=self.left_color, outline=self.left_color)
            if self.position == 1:
                self.arc1 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=120, extent=60, fill=self.left_color, outline=self.left_color)
                self.arc2 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=0, extent=60, fill=self.right_color, outline=self.right_color)
                self.canvas.tag_lower(self.arc1)
                self.canvas.tag_lower(self.arc2)
                self.canvas.tag_lower(self.big_circle)
                self.canvas.itemconfig(self.circles[1], fill='white', outline='white')
                self.canvas.itemconfig(self.circles[2], fill='white', outline='white')
                self.canvas.itemconfig(self.circles[4], fill=self.left_color, outline=self.left_color)
                self.canvas.itemconfig(self.circles[5], fill=self.right_color, outline=self.right_color)
                self.canvas.itemconfig(self.circles[3], fill=self.left_color, outline=self.left_color)
            elif self.position == 0:
                self.arc1 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=180, extent=60, fill=self.left_color, outline=self.left_color)
                self.arc2 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=300, extent=60, fill=self.right_color, outline=self.right_color)
                self.canvas.tag_lower(self.arc1)
                self.canvas.tag_lower(self.arc2)
                self.canvas.tag_lower(self.big_circle)
                self.canvas.itemconfig(self.circles[4], fill='white', outline='white')
                self.canvas.itemconfig(self.circles[5], fill='white', outline='white')
                self.canvas.itemconfig(self.circles[2], fill=self.left_color, outline=self.left_color)
                self.canvas.itemconfig(self.circles[1], fill=self.right_color, outline=self.right_color)
                self.canvas.itemconfig(self.circles[3], fill=self.left_color, outline=self.left_color)
            for i in range(0, 6):
                self.canvas.tag_raise(self.circles[i])
            if self.position != prev_position:
                if self.propagation[0] is True:
                    self.propagate_fluid(0, self.right_color)
                if self.propagation[3] is True:
                    self.propagate_fluid(3, self.left_color)

        def set_manual_position(self, position):    # TODO: Add in actual valve switching
            """Change the valve position after being clicked both visually and physically."""
            if self.canvas.window.instruments is None:
                self.set_position(position)
            elif self.hardware is None:
                self.assign_to_hardware()
            elif self.canvas.is_unlocked:
                self.hardware.switchvalve(position)
                self.set_position(position)

        def set_auto_position(self, position):    # TODO: Add in actual valve switching
            """Change the valve position after being clicked both visually and physically."""
            if self.hardware is None:
                raise ValueError
            else:
                self.hardware.switchvalve(position)
                self.set_position(position)

        def propagate_fluid(self, port, fluid_color):
            if port == 0 or port == 3:
                self.propagation = [False, False, False, False, False, False]
                self.propagation[port] = True
            if self.position == 1:
                pairs = [5, None, None, 4, 3, 0]
            elif self.position == 0:
                pairs = [1, 0, 3, 2, None, None]
            else:
                return
            pair = pairs[port]
            if pair is None:
                return  # Do nothing if port isn't connected
            if pair == 0 or port == 0:  # Propagate on the right side
                self.right_color = fluid_color
            elif pair == 3 or port == 3:  # Propagate on the left side
                self.left_color = fluid_color
            self.set_position(self.position)
            for line in self.fluid_lines[pair]:
                self.canvas.itemconfig(line, fill=fluid_color, outline=fluid_color)
            for (valve, port2) in self.connected_valves[pair]:
                valve.propagate_fluid(port2, fluid_color)

    class InjectionValve(Valve):
        def __init__(self, canvas, x, y, name, angle_off=0):
            """Initialize the injection valve and draw its unique parts."""
            super().__init__(canvas, x, y, name, angle_off)
            self.color1 = 'white'
            self.color2 = 'white'
            self.color3 = 'white'
            self.name = name
            self.position = 1
            self.inner_circle = self.canvas.create_circle(x, y, self.offset-self.small_radius, fill='dimgray', outline='dimgray', tag=self.name)
            self.canvas.tag_bind(name, '<Button-1>', lambda event: self.set_manual_position(self.position+1))

        def set_position(self, position, **kwargs):
            self.color1 = kwargs.pop('color1', self.color1)
            self.color2 = kwargs.pop('color2', self.color2)
            self.color3 = kwargs.pop('color3', self.color3)
            self.position = position % 2
            try:
                self.canvas.delete(self.arc1)
                self.canvas.delete(self.arc2)
                self.canvas.delete(self.arc3)
            except AttributeError:
                pass
            if self.position == 1:
                self.arc1 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=300+self.angle_off, extent=60, fill=self.color2, outline=self.color2)
                self.arc2 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=180+self.angle_off, extent=60, fill=self.color1, outline=self.color1)
                self.arc3 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=60+self.angle_off, extent=60, fill=self.color3, outline=self.color3)
                self.canvas.tag_lower(self.arc1)
                self.canvas.tag_lower(self.arc2)
                self.canvas.tag_lower(self.arc3)
                self.canvas.tag_lower(self.big_circle)
                self.canvas.itemconfig(self.circles[0], fill=self.color2, outline=self.color2)
                self.canvas.itemconfig(self.circles[1], fill=self.color2, outline=self.color2)
                self.canvas.itemconfig(self.circles[2], fill=self.color1, outline=self.color1)
                self.canvas.itemconfig(self.circles[3], fill=self.color1, outline=self.color1)
                self.canvas.itemconfig(self.circles[4], fill=self.color3, outline=self.color3)
                self.canvas.itemconfig(self.circles[5], fill=self.color3, outline=self.color3)
            elif self.position == 0:
                self.arc1 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=0, extent=60, fill=self.color3, outline=self.color3)
                self.arc2 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=240, extent=60, fill=self.color2, outline=self.color2)
                self.arc3 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=120, extent=60, fill=self.color1, outline=self.color1)
                self.canvas.tag_lower(self.arc1)
                self.canvas.tag_lower(self.arc2)
                self.canvas.tag_lower(self.arc3)
                self.canvas.tag_lower(self.big_circle)
                self.canvas.itemconfig(self.circles[0], fill=self.color3, outline=self.color3)
                self.canvas.itemconfig(self.circles[1], fill=self.color2, outline=self.color2)
                self.canvas.itemconfig(self.circles[2], fill=self.color2, outline=self.color2)
                self.canvas.itemconfig(self.circles[3], fill=self.color1, outline=self.color1)
                self.canvas.itemconfig(self.circles[4], fill=self.color1, outline=self.color1)
                self.canvas.itemconfig(self.circles[5], fill=self.color3, outline=self.color3)
            self.canvas.tag_raise(self.arc1)
            self.canvas.tag_raise(self.arc2)
            self.canvas.tag_raise(self.arc3)
            self.canvas.tag_raise(self.inner_circle)
            for i in range(0, 6):
                self.canvas.tag_raise(self.circles[i])

        def propagate_fluid(self, port, fluid_color):
            if self.position == 1:
                pairs = [1, 0, 3, 2, 5, 4]
                colors = [self.color2, self.color2, self.color1, self.color1, self.color3, self.color3]
            elif self.position == 0:
                pairs = [5, 2, 1, 4, 3, 0]
                colors = [self.color3, self.color2, self.color2, self.color1, self.color1, self.color3]
            colors[port] = fluid_color
            self.set_position(self.position)
            pair = pairs[port]
            if self.propagation[port] is True:
                for line in self.fluid_lines[pair]:
                    self.canvas.itemconfig(line, fill=colors[port], outline=colors[port])

        def set_manual_position(self, position):    # TODO: Add in actual valve switching
            """Change the valve position after being clicked both visually and physically."""
            if self.canvas.window.instruments is None:
                self.set_position(position)
            elif self.hardware is None:
                self.assign_to_hardware()
            elif self.canvas.is_unlocked:
                self.hardware.switchvalve(position)
                self.set_position(position)

    class FluidLevel():
        """Build a widget to show the fluid level in a syringe."""

        def __init__(self, canvas, x, y, **kwargs):
            """Start the FluidLevel object with default paramaters."""
            self.color = kwargs.pop('color', 'blue')
            self.background = kwargs.pop('background', 'white')
            self.orientation = kwargs.pop('orientation', 'left')
            self.name = kwargs.pop('name', '')
            self.canvas = canvas
            self.connected_valves = {'left': [], 'right': []}
            self.fluid_lines = {'left': [], 'right': []}
            self.opposite = {'left': 'right', 'right': 'left'}
            border = kwargs.pop('border', 10)
            # Use pop to remove kwargs that aren't a part of Canvas
            width = kwargs.get('width', 150)
            height = kwargs.get('height', 50)
            self.canvas.create_rectangle(x, y, x+width, y+height, fill="grey", outline="grey", tag=self.name)
            self.text = self.canvas.create_text(x+width/2, y+height/2, text=self.name, fill='white', font=("Helvetica", 12))
            self.max = self.canvas.create_rectangle(x+border, y+border, x+width-border, y+height-border, fill=self.background, outline=self.background, tag=self.name)
            self.level = self.canvas.create_rectangle(x+border, y+border, x+border, y+height-border, fill=self.background, outline=self.background, tag=self.name)

        def update(self, percent):
            """Update the fluid level to s given value."""
            percent = min(percent, 100)
            percent = max(percent, 0)

            x0, y0, x1, y1 = self.canvas.coords(self.max)
            if self.orientation == 'left':
                x1 = round((x1-x0)*percent/100) + x0
            elif self.orientation == 'right':
                x0 = x1 - round((x1-x0)*percent/100)
            self.canvas.coords(self.level, x0, y0, x1, y1)
            self.percent = percent
            if x1 == x0:
                self.canvas.itemconfig(self.level, fill=self.background, outline=self.background)
            else:
                self.canvas.itemconfig(self.level, fill=self.color, outline=self.color)
            if percent == 100:
                self.propagate_fluid(self.opposite[self.orientation], self.color)
            self.canvas.tag_raise(self.text)

        def connect(self, object_, position):
            if isinstance(object_, tuple):
                self.connected_valves[position].append(object_)
            else:
                self.fluid_lines[position].append(object_)   # TODO: Add way to associate real valve to diagram

        def propagate_fluid(self, side, fluid_color):
            exit_ = self.opposite[side]
            if side == self.orientation:    # if fluid is coming from exit of loop
                self.background = fluid_color
                self.canvas.itemconfig(self.max, fill=self.background, outline=self.background)
                for line in self.fluid_lines[exit_]:
                    self.canvas.itemconfig(line, fill=fluid_color, outline=fluid_color)
                for (valve, port2) in self.connected_valves[exit_]:
                    valve.propagate_fluid(port2, fluid_color)
            else:
                self.color = fluid_color
            self.update(0)

    class Lock():
        """Lock GUI item with onclick toggle."""

        def __init__(self, canvas, x, y):
            """Draw the lock."""
            self.x = x
            self.y = y
            self.canvas = canvas
            self.size = 100 * self.canvas.lock_scale
            self.state = 'locked'
            self.color = 'gold'
            self.canvas.create_rectangle(x, y+.8*self.size, x+self.size, y+1.8*self.size, fill=self.color, outline='', tag='lock')
            self.movable_rectangle = self.canvas.create_rectangle(x+.1*self.size, y+.4*self.size, x+.3*self.size, y+self.size, fill=self.color, outline='', tag='lock')
            self.canvas.create_rectangle(x+.7*self.size, y+.4*self.size, x+.9*self.size, y+self.size, fill=self.color, outline='', tag='lock')
            self.moveable_arc1 = self.canvas.create_arc(x+.1*self.size, y, x+.9*self.size, y+.8*self.size, start=0, extent=180, fill=self.color, outline='', tag='lock')
            self.moveable_arc2 = self.canvas.create_arc(x+.3*self.size, y+.2*self.size, x+.7*self.size, y+.6*self.size, start=0, extent=180, fill=self.canvas['background'], outline='', tag='lock')

        def toggle(self, state=None):
            """Toggle the visual state of the lock."""
            if state is not None:
                self.state = state
            elif self.state == 'locked':
                self.state = 'unlocked'
            else:
                self.state = 'locked'
            dist = .6*self.size
            if self.state == 'unlocked':
                self.canvas.move(self.movable_rectangle, 2*dist, 0)
                self.canvas.move(self.moveable_arc1, dist, 0)
                self.canvas.move(self.moveable_arc2, dist, 0)
            elif self.state == 'locked':
                self.canvas.move(self.movable_rectangle, -2*dist, 0)
                self.canvas.move(self.moveable_arc1, -dist, 0)
                self.canvas.move(self.moveable_arc2, -dist, 0)
            else:
                raise ValueError('Invalid lock state')

    def __init__(self, frame, main_window, **kwargs):
        """Set up initial variables and draw initial states."""
        self.sucrose = kwargs.pop('sucrose', False)
        super().__init__(frame, **kwargs)
        self.is_unlocked = False
        self.valve_scale = 1/2
        self.lock_scale = .2
        self.fluid_line_width = 20
        self.frame = frame
        self.window = main_window
        self.lock = self.Lock(self, 10, 10)
        self.tag_bind('lock', '<Button-1>', lambda event: self.lock_popup())
        # Set colors
        self.water_color = 'DodgerBlue4'
        self.air_color = 'RoyalBlue2'
        self.soap_color = 'SpringGreen4'
        self.sample_color = 'orange red'
        self.buffer_color = 'maroon4'
        self.sheath_color = 'goldenrod3'
        self.empty_color = 'grey30'
        # Add Elements
        self.draw_pumps()
        self.draw_valves()
        self.draw_loops()
        self.draw_fluid_lines()
        self.initialize()
        # Scale for computers smaller than 1800 log_width
        scale = self.frame.winfo_screenwidth()/1920
        self.scale("all", 0, 0, scale, scale)
        self.config(width=1250*scale, height=400*scale)

    def draw_pumps(self):
        """Draw the pumps."""
        self.pump1 = self.FluidLevel(self, 0, 75, height=50, color='black', orientation='right', name='pump1')
        self.pump2 = self.FluidLevel(self, 0, 275, height=50, color='black', orientation='right', name='pump2')

    def draw_valves(self):
        """Draw the valves."""
        row1_y = 100
        row2_y = 300
        #self.valve1 = self.InjectionValve(self, 300, row1_y, 'valve1')
        self.valve2 = self.SelectionValve(self, 300, row1_y, 'valve2')
        self.valve2.gui_names[5] = 'Waste'
        self.valve2.gui_names[3] = 'Run'
        self.valve2.propagation[3] = True
        self.valve2.colors[3] = 'black'
        self.valve3 = self.SampleValve(self, 700, row1_y, 'valve3')
        self.valve3.right_color = self.empty_color
        self.valve3.left_color = self.empty_color
        self.valve4 = self.SelectionValve(self, 1100, row1_y, 'valve4', angle_off=30)
        self.valve4.gui_names[5] = 'Run'
        self.valve4.gui_names[0] = 'Load'
        self.valve4.colors[0] = self.buffer_color
        self.valve4.gui_names[1] = 'Low Flow Soap'
        self.valve4.colors[1] = self.soap_color
        self.valve4.gui_names[2] = 'High Flow Soap'
        self.valve4.colors[2] = self.soap_color
        self.valve4.gui_names[3] = 'Water'
        self.valve4.colors[3] = self.water_color
        self.valve4.gui_names[4] = 'Air'
        self.valve4.colors[4] = self.air_color
        self.valve4.propagation = [True, True, True, True, True, False, True]
        self.valve6 = self.SelectionValve(self, 300, row2_y, 'valve5')
        self.valve6.gui_names[5] = 'Waste'
        self.valve6.gui_names[3] = 'Run'
        self.valve6.propagation[3] = True
        self.valve6.colors[3] = 'black'
        self.valve7 = self.SampleValve(self, 700, row2_y, 'valve6')
        self.valve8 = self.SelectionValve(self, 1100, row2_y, 'valve7', angle_off=30)
        self.valve8.gui_names[5] = 'Run'
        self.valve8.gui_names[0] = 'Load'
        self.valve8.colors[0] = self.sheath_color
        self.valve8.gui_names[1] = 'Low Flow Soap'
        self.valve8.colors[1] = self.soap_color
        self.valve8.gui_names[2] = 'High Flow Soap'
        self.valve8.colors[2] = self.soap_color
        self.valve8.gui_names[3] = 'Water'
        self.valve8.colors[3] = self.water_color
        self.valve8.gui_names[4] = 'Air'
        self.valve8.colors[4] = self.air_color
        self.valve8.propagation = [True, True, True, True, True, False, True]

    def draw_loops(self):
        """Draw the sample and buffer loops."""
        self.sample_loop = self.FluidLevel(self, 625, 0, height=30, color=self.empty_color, background='black', orientation='right', border=0, name='Sample')
        self.buffer_loop = self.FluidLevel(self, 625, 170, height=30, color=self.empty_color, background='black', orientation='right', border=0, name='Buffer')
        self.sheath_loop = self.FluidLevel(self, 625, 370, height=30, color=self.empty_color, background='black', orientation='right', border=0, name='Sheath')

    def draw_fluid_lines(self):
        """Draw the fluid lines and set associate them with the correct valves."""
        # Line from syringe to valve 1
        self.syringe_line = self.create_fluid_line('x', 150, 100, 110, color='black')
        self.tag_lower(self.syringe_line)
        self.valve2.connect(self.syringe_line, 3)
        # From Valve 2 to Waste
        x0, y0, x1, y1 = self.coords(self.valve2.circles[5])
        x_avg = math.floor((x0 + x1) / 2)
        self.waste_line = self.create_fluid_line('y', x_avg, y0, -50, color='grey30')
        self.valve2.connect(self.waste_line, 5)
        self.waste_text = self.create_text(x_avg+10, 10, anchor='se', text='Waste', fill='white', angle=90, font=("Helvetica", 12))
        self.tag_raise(self.waste_text)
        # From Valve 2 to Valve 3
        x0, y0, x1, y1 = self.coords(self.valve3.circles[3])
        y_avg = math.floor((y0 + y1) / 2)
        self.line_2to3 = self.create_fluid_line('x', x0, y_avg, -300)
        self.valve2.connect(self.line_2to3, 'center')
        self.valve2.connect((self.valve3, 3), 'center')
        self.valve3.connect(self.line_2to3, 3)
        self.valve3.connect((self.valve2, 'center'), 3)
        # From Valve 3 to sample loop
        x0, y0, x1, y1 = self.coords(self.valve3.circles[4])
        y_avg = math.floor((y0 + y1) / 2)
        self.sample_line_1 = self.create_fluid_line('x', x0, y_avg, -40)
        self.sample_line_2 = self.create_fluid_line('y', x0-40, y_avg, -40)
        self.valve3.connect(self.sample_line_1, 4)
        self.valve3.connect(self.sample_line_2, 4)
        self.valve3.connect((self.sample_loop, 'left'), 4)
        self.sample_loop.connect(self.sample_line_1, 'left')
        self.sample_loop.connect(self.sample_line_2, 'left')
        self.sample_loop.connect((self.valve3, 4), 'left')
        x0, y0, x1, y1 = self.coords(self.valve3.circles[5])
        y_avg = math.floor((y0 + y1) / 2)
        self.sample_line_4 = self.create_fluid_line('x', x1, y_avg, 40)
        self.sample_line_3 = self.create_fluid_line('y', x1+40, y_avg, -40)
        self.valve3.connect(self.sample_line_3, 5)
        self.valve3.connect(self.sample_line_4, 5)
        self.valve3.connect((self.sample_loop, 'right'), 5)
        self.sample_loop.connect(self.sample_line_3, 'right')
        self.sample_loop.connect(self.sample_line_4, 'right')
        self.sample_loop.connect((self.valve3, 5), 'right')
        self.tag_lower(self.sample_line_2)
        self.tag_lower(self.sample_line_3)
        # From Valve 3 to buffer loop
        x0, y0, x1, y1 = self.coords(self.valve3.circles[2])
        y_avg = math.floor((y0 + y1) / 2)
        self.buffer_line_1 = self.create_fluid_line('x', x0, y_avg, -40)
        self.buffer_line_2 = self.create_fluid_line('y', x0-40, y_avg, 40)
        self.valve3.connect(self.buffer_line_1, 2)
        self.valve3.connect(self.buffer_line_2, 2)
        self.valve3.connect((self.buffer_loop, 'left'), 2)
        self.buffer_loop.connect(self.buffer_line_1, 'left')
        self.buffer_loop.connect(self.buffer_line_2, 'left')
        self.buffer_loop.connect((self.valve3, 2), 'left')
        x0, y0, x1, y1 = self.coords(self.valve3.circles[1])
        y_avg = math.floor((y0 + y1) / 2)
        self.buffer_line_4 = self.create_fluid_line('x', x1, y_avg, 40)
        self.buffer_line_3 = self.create_fluid_line('y', x1+40, y_avg, 40)
        self.valve3.connect(self.buffer_line_3, 1)
        self.valve3.connect(self.buffer_line_4, 1)
        self.valve3.connect((self.buffer_loop, 'right'), 1)
        self.buffer_loop.connect(self.buffer_line_3, 'right')
        self.buffer_loop.connect(self.buffer_line_4, 'right')
        self.buffer_loop.connect((self.valve3, 1), 'right')
        self.tag_lower(self.buffer_line_2)
        self.tag_lower(self.buffer_line_3)
        # From Valve 3 to Valve 4
        x0, y0, x1, y1 = self.coords(self.valve3.circles[0])
        y_avg = math.floor((y0 + y1) / 2)
        self.line_3to4 = self.create_fluid_line('x', x1, y_avg, 300)
        self.valve3.connect(self.line_3to4, 0)
        self.valve4.connect(self.line_3to4, 'center')
        self.valve4.connect((self.valve3, 0), 'center')
        # From Valve 4 to Cell
        x0, y0, x1, y1 = self.coords(self.valve4.circles[5])
        y_avg = math.floor((y0 + y1) / 2)
        self.cell_line = self.create_fluid_line('x', x1, y_avg, 100)
        self.valve4.connect(self.cell_line, 5)
        self.cell_text = self.create_text(x1+100, y_avg+10, anchor='se', text='To Cell', fill='white', font=("Helvetica", 12))
        # From Valve 4 to Load
        x0, y0, x1, y1 = self.coords(self.valve4.circles[0])
        y_avg = math.floor((y0 + y1) / 2)
        self.load_line = self.create_fluid_line('x', x1, y_avg, 100, color=self.buffer_color)
        self.valve4.connect(self.load_line, 0)
        self.load_text = self.create_text(x1+100, y_avg+10, anchor='se', text='From Load', fill='white', font=("Helvetica", 12))
        # From Valve 4 to cleaning
        x0, y0, x1, y1 = self.coords(self.valve4.circles[4])
        x_avg = math.floor((x0 + x1) / 2)
        self.air_line = self.create_fluid_line('y', x_avg, y0, -50, color=self.air_color)
        self.air_text = self.create_text(x_avg+10, 10, anchor='se', text='Air', fill='white', angle=90, font=("Helvetica", 12))
        self.tag_raise(self.air_text)
        x0, y0, x1, y1 = self.coords(self.valve4.circles[3])
        x_avg = math.floor((x0 + x1) / 2)
        self.water_line = self.create_fluid_line('y', x_avg, y0, -100, color=self.water_color)
        self.water_text = self.create_text(x_avg+10, 10, anchor='se', text='Water', fill='white', angle=90, font=("Helvetica", 12))
        self.tag_raise(self.water_text)
        x0, y0, x1, y1 = self.coords(self.valve4.circles[1])
        x_avg = math.floor((x0 + x1) / 2)
        self.low_soap_line = self.create_fluid_line('y', x_avg, y1, 50, color=self.soap_color)
        self.low_soap_text = self.create_text(x_avg+10, y1+60, anchor='sw', text='Low Soap', fill='white', angle=90, font=("Helvetica", 10))
        self.tag_raise(self.low_soap_text)
        x0, y0, x1, y1 = self.coords(self.valve4.circles[2])
        x_avg = math.floor((x0 + x1) / 2)
        self.high_soap_line = self.create_fluid_line('y', x_avg, y1, 65, color=self.soap_color)
        self.high_soap_text = self.create_text(x_avg+10, y1+75, anchor='sw', text='High Soap', fill='white', angle=90, font=("Helvetica", 10))
        self.tag_raise(self.high_soap_text)
        # =======================================================================
        # Line from syringe to valve 6
        self.syringe_line_2 = self.create_fluid_line('x', 150, 300, 110, color='black')
        self.tag_lower(self.syringe_line_2)
        self.valve6.connect(self.syringe_line_2, 3)
        # From Valve 6 to Waste
        x0, y0, x1, y1 = self.coords(self.valve6.circles[5])
        x_avg = math.floor((x0 + x1) / 2)
        self.waste_line_2 = self.create_fluid_line('y', x_avg, y0, -50, color='grey30')
        self.valve6.connect(self.waste_line_2, 5)
        self.waste_text_2 = self.create_text(x_avg+10, 210, anchor='se', text='Waste', fill='white', angle=90, font=("Helvetica", 12))
        self.tag_raise(self.waste_text_2)
        # From Valve 6 to Valve 7
        x0, y0, x1, y1 = self.coords(self.valve7.circles[3])
        y_avg = math.floor((y0 + y1) / 2)
        self.line_6to7 = self.create_fluid_line('x', x0, y_avg, -300)
        self.valve6.connect(self.line_6to7, 'center')
        self.valve6.connect((self.valve7, 3), 'center')
        self.valve7.connect(self.line_6to7, 3)
        self.valve7.connect((self.valve6, 'center'), 3)
        # From Valve 7 to sheath loop
        x0, y0, x1, y1 = self.coords(self.valve7.circles[2])
        y_avg = math.floor((y0 + y1) / 2)
        self.sheath_line_1 = self.create_fluid_line('x', x0, y_avg, -40)
        self.sheath_line_2 = self.create_fluid_line('y', x0-40, y_avg, 40)
        self.valve7.connect(self.sheath_line_1, 2)
        self.valve7.connect(self.sheath_line_2, 2)
        self.valve7.connect((self.sheath_loop, 'left'), 2)
        self.sheath_loop.connect(self.sheath_line_1, 'left')
        self.sheath_loop.connect(self.sheath_line_2, 'left')
        self.sheath_loop.connect((self.valve7, 2), 'left')
        x0, y0, x1, y1 = self.coords(self.valve7.circles[1])
        y_avg = math.floor((y0 + y1) / 2)
        self.sheath_line_4 = self.create_fluid_line('x', x1, y_avg, 40)
        self.sheath_line_3 = self.create_fluid_line('y', x1+40, y_avg, 40)
        self.valve7.connect(self.sheath_line_3, 1)
        self.valve7.connect(self.sheath_line_4, 1)
        self.valve7.connect((self.sheath_loop, 'right'), 1)
        self.sheath_loop.connect(self.sheath_line_3, 'right')
        self.sheath_loop.connect(self.sheath_line_4, 'right')
        self.sheath_loop.connect((self.valve7, 1), 'right')
        self.tag_lower(self.sheath_line_2)
        self.tag_lower(self.sheath_line_3)
        # From Valve 7 to Valve 8
        x0, y0, x1, y1 = self.coords(self.valve7.circles[0])
        y_avg = math.floor((y0 + y1) / 2)
        self.line_7to8 = self.create_fluid_line('x', x1, y_avg, 300)
        self.valve7.connect(self.line_7to8, 0)
        self.valve8.connect(self.line_7to8, 'center')
        self.valve8.connect((self.valve7, 0), 'center')
        # From Valve 8 to Cell
        x0, y0, x1, y1 = self.coords(self.valve8.circles[5])
        y_avg = math.floor((y0 + y1) / 2)
        self.cell_line_2 = self.create_fluid_line('x', x1, y_avg, 100)
        self.valve8.connect(self.cell_line_2, 5)
        self.cell_text_2 = self.create_text(x1+100, y_avg+10, anchor='se', text='To Cell', fill='white', font=("Helvetica", 12))
        # From Valve 8 to Load
        x0, y0, x1, y1 = self.coords(self.valve8.circles[0])
        y_avg = math.floor((y0 + y1) / 2)
        self.load_line_2 = self.create_fluid_line('x', x1, y_avg, 100, color=self.sheath_color)
        self.valve8.connect(self.load_line_2, 0)
        self.load_text_2 = self.create_text(x1+100, y_avg+10, anchor='se', text='From Load', fill='white', font=("Helvetica", 12))
        # From Valve 8 to cleaning
        x0, y0, x1, y1 = self.coords(self.valve8.circles[4])
        x_avg = math.floor((x0 + x1) / 2)
        self.air_line_2 = self.create_fluid_line('y', x_avg, y0, -50, color=self.air_color)
        self.air_text_2 = self.create_text(x_avg+10, 210, anchor='se', text='Air', fill='white', angle=90, font=("Helvetica", 12))
        self.tag_raise(self.air_text_2)
        x0, y0, x1, y1 = self.coords(self.valve8.circles[3])
        x_avg = math.floor((x0 + x1) / 2)
        self.water_line_2 = self.create_fluid_line('y', x_avg, y0, -100, color=self.water_color)
        self.water_text_2 = self.create_text(x_avg+10, 210, anchor='se', text='Water', fill='white', angle=90, font=("Helvetica", 12))
        self.tag_raise(self.water_text_2)
        x0, y0, x1, y1 = self.coords(self.valve8.circles[1])
        x_avg = math.floor((x0 + x1) / 2)
        self.low_soap_line_2 = self.create_fluid_line('y', x_avg, y1, 50, color=self.soap_color)
        self.low_soap_text_2 = self.create_text(x_avg+10, y1+60, anchor='sw', text='Low Soap', fill='white', angle=90, font=("Helvetica", 10))
        self.tag_raise(self.low_soap_text_2)
        x0, y0, x1, y1 = self.coords(self.valve8.circles[2])
        x_avg = math.floor((x0 + x1) / 2)
        self.high_soap_line_2 = self.create_fluid_line('y', x_avg, y1, 65, color=self.soap_color)
        self.high_soap_text_2 = self.create_text(x_avg+10, y1+75, anchor='sw', text='High Soap', fill='white', angle=90, font=("Helvetica", 10))
        self.tag_raise(self.high_soap_text_2)

    def initialize(self):
        """Set initial levels, colors, and valve positions."""
        self.pump1.update(100)
        self.pump2.update(100)
        self.sample_loop.update(100)
        self.buffer_loop.update(100)
        #self.valve1.set_position(0, color1='black')
        self.valve2.set_position(5)
        self.valve3.set_position(1)
        self.valve4.set_position('Load')
        self.valve6.set_position(5)
        self.valve7.set_position(0)
        self.valve8.set_position('Load')

    def create_circle(self, x, y, r, **kwargs):
        """Draw a circle by center and radius."""
        return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)

    def create_fluid_line(self, direction, x, y, length, **kwargs):
        """Draw a fluid line from a location by length and direction."""
        width = kwargs.pop('width', self.fluid_line_width)
        color = kwargs.pop('color', 'grey30')
        r = width/2
        if direction == 'x':
            if length > 0:
                return self.create_rectangle(x-r, y-r, x+length+r, y+r, fill=color, outline=color)
            else:
                return self.create_rectangle(x+length-r, y-r, x+r, y+r, fill=color, outline=color)
        elif direction == 'y':
            if length > 0:
                return self.create_rectangle(x-r, y-r, x+r, y+length+r, fill=color, outline=color)
            else:
                return self.create_rectangle(x-r, y+length-r, x+r, y+r, fill=color, outline=color)

    def set_unlock_state(self, state=None):
        """Set the GUI lock state."""
        if state is None:
            self.is_unlocked = not self.is_unlocked
        else:
            self.is_unlocked = state
        if self.is_unlocked:
            self.lock.toggle('unlocked')
        else:
            self.lock.toggle('locked')

    def manual_switch_lock(self):
        """Lock the GUI and the lock icon."""
        if self.is_unlocked:
            self.is_unlocked = False
        else:
            self.lock_popup()

    def lock_popup(self):
        """Popup a window to unlock the GUI with a password."""
        def check_password(password):
            if password == 'asaxsisgr8':
                self.set_unlock_state(True)
                win.destroy()
        if self.is_unlocked:
            self.set_unlock_state(False)
        else:
            print('Test')
            win = tk.Toplevel()
            win.wm_title("Unlock?")
            label = tk.Label(win, text='Password?')
            label.grid(row=0, column=0)
            pass_entry = tk.Entry(win, show='*')
            pass_entry.grid(row=0, column=1)
            pass_entry.focus()
            pass_entry.bind("<Return>", lambda event: check_password(pass_entry.get()))
            ok_button = tk.Button(win, text="Unlock", command=lambda: check_password(pass_entry.get()))
            ok_button.grid(row=1, column=0)
            cancel_button = tk.Button(win, text="Cancel", command=win.destroy)
            cancel_button.grid(row=1, column=1)


if __name__ == "__main__":
    window = tk.Tk()
    window.instruments = None
    window.flowpath = FlowPath(window, window)
    window.flowpath.grid(row=0, column=0)
    window.mainloop()
