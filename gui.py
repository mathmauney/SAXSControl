import tkinter as tk
from widgets import FluidLevel


def runPump(meter):
    meter.tick()


main_window = tk.Tk()
main_window.title('Main Window')

oil_ticksize = tk.IntVar(value=5)

exit_button = tk.Button(main_window, text='Exit', width=20, command=main_window.destroy)
exit_button.grid(row=1, column=0, columnspan=5, pady=(10, 0))

oil_meter = FluidLevel(main_window, color='black', ticksize=oil_ticksize)
oil_meter.update(100)
oil_meter.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

oil_refill_button = tk.Button(main_window, text='Refill Oil', command=lambda: oil_meter.update(100))
oil_refill_button.grid(row=3, column=0)

oil_speed_scale = tk.Scale(main_window, variable=oil_ticksize, from_=1, to=100, orient='horizontal')
oil_speed_scale.grid(column=1, row=3)

run_pump_button = tk.Button(main_window, text='Run Pump', width=15, command=lambda: runPump(oil_meter))
run_pump_button.grid(row=2, column=2)

main_window.mainloop()
