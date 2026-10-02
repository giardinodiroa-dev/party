"""Render one subject (the saucer) in six looks at 2x with the real shader, plus close-ups."""
import sys, numpy as np; sys.path.insert(0, '/home/CROWN/party')
from PyQt6.QtGui import QGuiApplication, QImage, QOffscreenSurface, QOpenGLContext, QSurfaceFormat, QPainter, QColor
from PyQt6.QtCore import QSize, QRectF
from OpenGL import GL as gl
app = QGuiApplication(sys.argv)
from party.ui.aura import AuraPipeline, AuraParams
from PyQt6.QtOpenGL import QOpenGLFramebufferObject
OUT = '/home/CROWN/party/exam/aesthetics'
W, H = 1920, 1080
black = np.zeros((H, W, 4), np.uint8); black[:, :, 3] = 255
fmt = QSurfaceFormat(); fmt.setVersion(3, 3); fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
surf = QOffscreenSurface(); surf.setFormat(fmt); surf.create(); ctx = QOpenGLContext(); ctx.setFormat(fmt); ctx.create(); ctx.makeCurrent(surf)
pipe = AuraPipeline(W, H); pipe.init()
out = QOpenGLFramebufferObject(QSize(W, H), QOpenGLFramebufferObject.Attachment.NoAttachment, gl.GL_TEXTURE_2D, gl.GL_RGBA8)
LOOKS = ["A-chrome", "B-holo", "C-toon", "D-pearl", "E-neon", "F-ghost"]
sheet = QImage(3 * 640, 2 * 360, QImage.Format.Format_ARGB32_Premultiplied); sheet.fill(QColor('#07070a')); sp = QPainter(sheet)
for i, name in enumerate(LOOKS):
    p = AuraParams(hue=200, loud=0.4, bass=0.4, flash=0.2, width=2.0, waves=0, ghost=False, astral=True); p.spectrum = np.zeros(32, 'float32')
    size = 0.9; bw = size * H / W
    p.bodies = [{"mode": 2, "x": 0.5, "y": 0.5, "size": size, "joints": None, "woman": 0.0, "yaw": 0.6, "bank": 0.0, "tint": (1, 1, 1), "alpha": 1.0,
                 "engine": 0.6, "look": i, "behind": 0.0, "rect": (0.5 - bw / 2, 0.5 - size / 2, bw, size)}]
    p.time = 3.0; pipe.upload(black); pipe.render(p, out.handle(), (W, H))
    img = out.toImage(False).mirrored(False, True)
    bg = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied); bg.fill(QColor('#07070a')); q = QPainter(bg); q.drawImage(0, 0, img); q.end()
    bg.save(f'{OUT}/{name}.png')
    bg.copy(int(W * 0.5 - 420), int(H * 0.5 - 330), 840, 420).save(f'{OUT}/{name}-close.png')
    sp.drawImage(QRectF((i % 3) * 640, (i // 3) * 360, 640, 360), bg)
    print(name, 'ok')
sp.end(); sheet.save(f'{OUT}/sheet.png'); print('sheet')
