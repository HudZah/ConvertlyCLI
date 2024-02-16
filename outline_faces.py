import cv2
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
image = cv2.imread('/Users/hudzah/Downloads/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/awfwfa/picture.jpg')
gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
faces = face_cascade.detectMultiScale(gray_image, 1.1, 4)
for (x, y, w, h) in faces:
    cv2.rectangle(image, (x, y), (x+w, y+h), (255, 0, 0), 2)
cv2.imwrite('/Users/hudzah/Downloads/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/awfwfa/outlined.jpg', image)
