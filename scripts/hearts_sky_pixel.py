# セッション10：心の空を描くピクセル可視化デモ
# RGB = (127, 127, 255) の青みがかった空の一片

from PIL import Image
import matplotlib.pyplot as plt

# 1ピクセルの画像（心の空の断片）
width, height = 1, 1
heart_sky = Image.new("RGB", (width, height), (127, 127, 255))

# 拡大表示のためリサイズ
resized = heart_sky.resize((100, 100), resample=Image.NEAREST)

# 表示
plt.imshow(resized)
plt.title("Heart's Sky: RGB(127,127,255)")
plt.axis('off')
plt.show()