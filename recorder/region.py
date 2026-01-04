import tkinter as tk

class RegionSelector(tk.Toplevel):
    def __init__(self, root):
        super().__init__(root)
        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.3)
        self.configure(bg="black")
        self.canvas = tk.Canvas(self, cursor="cross", bg="black")
        self.canvas.pack(fill="both", expand=True)
        self.start = None
        self.rect = None
        self.region = None
        self.canvas.bind("<ButtonPress-1>", self.on_start)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_end)

    def on_start(self, e):
        self.start = (e.x, e.y)
        self.rect = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2)

    def on_drag(self, e):
        self.canvas.coords(self.rect, *self.start, e.x, e.y)

    def on_end(self, e):
        x1, y1 = self.start
        self.region = (min(x1, e.x), min(y1, e.y), abs(e.x - x1), abs(e.y - y1))
        self.destroy()
