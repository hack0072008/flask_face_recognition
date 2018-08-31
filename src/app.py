#!/usr/bin/python
#-*-coding:utf-8-*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4
# copyright 2018 Sengled, Inc.
# All Rights Reserved.

# @author: Zhangyh, Sengled, Inc.

from flask_uploads import UploadSet, configure_uploads

from flask_uploads import ALL,ARCHIVES,AUDIO,DATA,DEFAULTS,DOCUMENTS,EXECUTABLES,IMAGES,PY3,SCRIPTS,TEXT

from flask import request, Flask, redirect, url_for, render_template, Response

from flask import  make_response
from flask import redirect
from flask import abort
from flask import send_from_directory
from flask import jsonify

from werkzeug import secure_filename

import os

import face_recognition
import json
import urllib

#words gbk
import sys
reload(sys) 
sys.setdefaultencoding('utf8')

golbal_tolerance = 0.4
#golbal_tolerance = 0.3

#rectangle setting
golbal_rectangle_color = (0,0,255)
golbal_rectangle_line_size = 8

#person_note setting
golbal_person_name_font_size = 14
golbal_persion_name_font = 'xxxx'
golbal_persion_name_color = 'yyyy'


#cut image
import PIL


#ocr
import pytesseract
from PIL import Image

#draw
import cv2


#camera
from camera import VideoCamera


app = Flask(__name__)


#分类定义uploadset
#image
app.config['UPLOADED_IMAGES_DEST'] = os.path.join(os.getcwd(), 'upload/images')
app.config['UPLOADED_IMAGES_HEAD'] = os.path.join(os.getcwd(), 'upload/head')
app.config['UPLOADED_IMAGES_FRAME'] = os.path.join(os.getcwd(), 'upload/../static/img/frame')
app.config['UPLOADED_IMAGES_DATABASE'] = os.path.join(os.getcwd(), 'upload/database')
app.config['UPLOADED_IMAGES_ALLOW'] = IMAGES
images = UploadSet('IMAGES')
configure_uploads(app, images)

#audio
app.config['UPLOADED_AUDIO_DEST'] = os.path.join(os.getcwd(), 'upload/audio')
app.config['UPLOADED_AUDIO_ALLOW'] = AUDIO
audios = UploadSet('AUDIO')
configure_uploads(app, audios)


@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST' and 'upload1' in request.files and 'upload2' in request.files:
        #print request.files['upload1'].mimetype
        #print request.files['upload1'].filename

        #获取原始文件名和安全文件名(剔除中文)
        file1 = request.files['upload1']
        filename1 = secure_filename(file1.filename)
        #print file1
        #print filename1

        file2 = request.files['upload2']
        filename2 = secure_filename(file2.filename)

        try:
            #根据文件后缀名进行分类存储和分类展示
            if filename1.split('.')[1] in list(IMAGES) and filename2.split('.')[1] in list(IMAGES):
                #清理同名文件
                if os.path.exists(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename1)):
                    os.remove(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename1))
                if os.path.exists(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename2)):
                    os.remove(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename2))

                #保存新文件
                file_name1 = images.save(file1)
                file_name2 = images.save(file2)

                param = {}
                param['filename1'] = file_name1
                param['filename2'] = file_name2
                param['filename1_frame'] = None
                param['filename2_frame'] = None
                param['result'] = None
                param['filename1_text'] = None
                param['person_name1'] = None
                param['person_name2'] = None

                #检测有人脸做人脸操作
                face_result = None
                if check_image_faces(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename1)) and check_image_faces(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename2)):
                    #截取头像
                    cut_image_head(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename1), app.config['UPLOADED_IMAGES_HEAD'], file_name1.split('.')[0] + '_Head')
                    cut_image_head(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename2), app.config['UPLOADED_IMAGES_HEAD'], file_name2.split('.')[0] + '_Head')

                    #在 database 中识别出人名
                    person_name1 = 'null'
                    person_name2 = 'null'
                    person_name1 = image_compare_name(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename1), app.config['UPLOADED_IMAGES_DATABASE'], type = 'local_dir')
                    person_name2 = image_compare_name(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename2), app.config['UPLOADED_IMAGES_DATABASE'], type = 'local_dir')

                    if person_name1 == 'null':
                        print('warning.....not found this person name file[%s]' % (os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename1)))
                    if person_name2 == 'null':
                        print('warning.....not found this person name file[%s]' % (os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename2)))
                    print('============ person_name1[%s] person_name2[%s]' % (person_name1, person_name2))

                    #标记人脸方框 和 人名
                    filename1_frame = draw_image_head(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename1), app.config['UPLOADED_IMAGES_FRAME'], file_name1.split('.')[0] + '_Frame')
                    filename2_frame = draw_image_head(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename2), app.config['UPLOADED_IMAGES_FRAME'], file_name2.split('.')[0] + '_Frame')
                    param['filename1_frame'] = filename1_frame
                    param['filename2_frame'] = filename2_frame

                    #compare faces
                    result = ''
                    result = face_compare(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename1), os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename2))
                    #print result
                    #print type(result)

                    if result is None:
                        return jsonify( { "errno" : 1002,"errmsg" : "参数校验失败 or 文件检查失败" } )
                    elif result:
                        face_result = 1
                    else:
                        face_result = 0
                #ocr words
                filename1_words = tesseract_image_words(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename1))

                #show, param
                param['result'] = str(face_result)
                param['filename1_text'] = filename1_words
                param['person_name1'] = person_name1
                param['person_name2'] = person_name2

                print param['filename1_text']
                return redirect(url_for('show_image', param = urllib.urlencode(param)))

            elif filename1.split('.')[1] in list(AUDIO):
                if os.path.exists(os.path.join(app.config['UPLOADED_AUDIO_DEST'], filename1)):
                    os.remove(os.path.join(app.config['UPLOADED_AUDIO_DEST'], filename1))
                file_name1 = audios.save(file1)
                return redirect(url_for('show_audio', name=file_name1))
            else:
                return redirect(url_for('notallow', file_name = filename1))
        except Exception,e:
            print('upload exception:%s' % str(e))
            return jsonify( { "errno" : 1001,"errmsg" : u"上传失败" } )

    return render_template('upload.html')

def check_image_faces(image_path):
    if not image_path:
        print 'check param error.'

    faces = []
    try:
        image = face_recognition.load_image_file(image_path)
        faces = face_recognition.face_locations(image)
    except Exception,e:
        print('check_image_faces exception:%s' % str(e))
        return False

    if len(faces) > 0:
        return True
    else:
        return False

def face_compare(photo1_path, photo2_path):
    #check param and file is exist
    if not photo1_path or not photo2_path:
        print 'param check error, please check.'
        return None
    elif not os.path.exists(photo1_path) or not os.path.exists(photo2_path):
        print 'file is not exist, please check.'
        return None

    photo1_image = face_recognition.load_image_file(photo1_path)
    photo2_image = face_recognition.load_image_file(photo2_path)

    photo1_encoding = face_recognition.face_encodings(photo1_image)[0]
    photo2_encoding = face_recognition.face_encodings(photo2_image)[0]

    print 'golbal_tolerance:' + str(golbal_tolerance)
    results = face_recognition.compare_faces([photo1_encoding], photo2_encoding, tolerance=golbal_tolerance)
    #print type(results)
    #print type(results[0])
    print results[0]

    return results[0]

def image_compare_name(photo_path, database, type = 'local_dir', tolerance = golbal_tolerance):
    #check param and file is exist
    if not photo_path or not database or not type or not tolerance:
        print 'param check error, please check.'
        return None
    elif type ==  'local_dir':
        if not os.path.exists(photo_path) or not os.path.exists(database):
            print('[%s] or [%s] is not exist, please check.' % (photo_path, database))
            return None

        if not os.path.isfile(photo_path) or not os.path.isdir(database):
            print('[%s] is not file or [%s] is not dir, please check.' % (photo_path, database))
            return None
    else:
        pass

    photo_image = face_recognition.load_image_file(photo_path)
    photo_encoding = face_recognition.face_encodings(photo_image)[0]

    print 'golbal_tolerance:' + str(golbal_tolerance)
    files_list = os.listdir(database)
    filenames_list = []
    for item in files_list:
        item_image = face_recognition.load_image_file(os.path.join(database, item))
        item_encoding = face_recognition.face_encodings(item_image)[0]
        ret = face_recognition.compare_faces([photo_encoding], item_encoding, tolerance=golbal_tolerance)
        print('unknow_image[%s] database_image[%s] compare_ret[%s]' % (photo_path, os.path.join(database, item), str(ret[0])))

        if ret[0] == True:
            filenames_list.append(item.split('.')[0])
        else:
            pass

    if len(filenames_list) >= 1:
        print('unknow_image[%s] database[%s] find count[%s], person_name[%s]' % (photo_path, database, str(len(filenames_list)), filenames_list[0]))
        return filenames_list[0]
    else:
        print('unknow_image[%s] database[%s] find count[%s] not detect' % (photo_path, database, str(len(filenames_list))))
        return None

def cut_image_head(image_path, new_image_path, filename_prefix):
    if not image_path or not new_image_path or not filename_prefix:
        print 'check param error.'
        return False
    print('image_src[%s] new_image_path[%s] filename_prefix[%s]' % (image_path, new_image_path, filename_prefix))

    image = face_recognition.load_image_file(image_path)
    image_faces = face_recognition.face_locations(image)

    print("I found {} face(s) in this photograph.".format(len(image_faces)))
    for index in range(0, len(image_faces)):
        try:
            top, right, bottom, left = image_faces[index]
            image_head = image[top:bottom, left:right]
            pil_image = PIL.Image.fromarray(image_head)
            new_filename = os.path.join(new_image_path, filename_prefix + '_' + str(index) + '.jpg')

            file = open(new_filename, 'w')
            print('No[%s] image file [%s] create succ.' % (str(index + 1), new_filename))

            pil_image.save(fp = file)
            file.close()
            print('No[%s] image file [%s] save   succ.' % (str(index + 1), new_filename))
        except Exception,e:
            print('cut_image_head exception:[%s], continue...' % str(e))
            #return False
            continue
    return True

def draw_image_head(image_path, new_image_path, filename_prefix):
    if not image_path or not new_image_path or not filename_prefix:
        print 'check param error.'
        return None
    print('image_src[%s] new_image_path[%s] filename_prefix[%s]' % (image_path, new_image_path, filename_prefix))

    image = face_recognition.load_image_file(image_path)
    image_faces = face_recognition.face_locations(image)

    print("I found {} face(s) in this photograph.".format(len(image_faces)))
    new_filename = os.path.join(new_image_path, filename_prefix + '.jpg')
    if os.path.exists(new_filename):
        os.remove(new_filename)

    im = cv2.imread(image_path)
    for index in range(0, len(image_faces)):
        try:
            top, right, bottom, left = image_faces[index]
            cv2.rectangle(im, (right, bottom), (left,top), golbal_rectangle_color , golbal_rectangle_line_size)
            print('image[%s] No[%s] face draw succ.' % (image_path, str(index + 1)))
        except Exception,e:
            print('draw_image_head No[%s]face exception:[%s], continue...' % (str(index + 1), str(e)))
            #return None
            continue
    cv2.imwrite(new_filename,im)
    print('image[%s] draw succ, new_image[%s].' % (image_path, new_filename))
    return filename_prefix + '.jpg'

#lang:chi_sim, eng
def tesseract_image_words(image_path, lang = 'chi_sim'):
    if not image_path:
        print 'check param error.'
        return None
    print('image_src[%s] lang[%s]' % (image_path, lang))

    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang=lang)
    except Exception, e:
        print 'tesseract image exception...'
        return None

    print('image[%s] tesseract image succ, words[%d].' % (image_path, len(text)))
    return text

def get_url_param(param, delimiter = '&'):
    param_json = {}
    for item in param.split(delimiter):
        param_json[item.split('=')[0]] = item.split('=')[1]
    #print param_json
    return param_json


@app.route('/show_image/<param>')
def show_image(param):
    if param is None:
        abort(404)

    #get param
    param = urllib.unquote(param)
    #print param

    #get param json
    '''
    filename1 = param.split('&')[0].split('=')[1]
    filename2 = param.split('&')[1].split('=')[1]
    filename1_frame = param.split('&')[2].split('=')[1]
    filename2_frame = param.split('&')[3].split('=')[1]
    result = param.split('&')[4].split('=')[1]
    '''
    param_json = get_url_param(param)
    print param_json

    filename1 = param_json['filename1']
    filename2 = param_json['filename2']
    filename1_frame = param_json['filename1_frame']
    filename2_frame = param_json['filename2_frame']
    result = param_json['result']
    filename1_text = param_json['filename1_text'].encode('unicode-escape').decode('string_escape')
    person_name1 = param_json['person_name1']
    person_name2 = param_json['person_name2']
    print '====================================='
    print filename1_text
    print('filename1[%s] filename2[%s] result[%s] person_name1[%s] person_name2[%s]' % (filename1, filename2, result, person_name1, person_name2))

    url1 = images.url(filename1)
    url2 = images.url(filename2)
    #url3 = images.url(filename1_frame)
    #url4 = images.url(filename2_frame)
    url3 = filename1_frame
    url4 = filename2_frame
    return render_template('show_image.html', url1=url1, url2=url2, url3=url3, url4=url4, result = result, filename1_text = filename1_text, person_name1 = person_name1, person_name2 = person_name2)

@app.route('/show_audio/<name>')
def show_audio(name):
    if name is None:
        abort(404)
    url = audios.url(name)
    return render_template('show_audio.html', url=url, name=name)

@app.route('/notallow/<file_name>')
def notallow(file_name):
    if file_name is None:
        abort(404)
    return render_template('notallow.html', url = file_name)

@app.route('/download', methods=['POST', 'GET'])
def download():
    if request.method=="POST" and request.form.get('filename', None) is not None:
        file_name = request.form.get('filename', None)
        if file_name.split('.')[1] in list(AUDIO):
            local_path = os.path.join(app.config['UPLOADED_AUDIO_DEST'], file_name)
            if os.path.isfile(local_path):
                return send_from_directory(app.config['UPLOADED_AUDIO_DEST'], file_name, as_attachment = True)
            else:
                abort(404)
        if file_name.split('.')[1] in list(IMAGES):
            local_path = os.path.join(app.config['UPLOADED_IMAGES_DEST'], file_name)
            if os.path.isfile(local_path):
                return send_from_directory(app.config['UPLOADED_IMAGES_DEST'], file_name, as_attachment = True)
            else:
                abort(404)
        else:
            return redirect(url_for('notallow', file_name = file_name))
    return render_template('download.html')

def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(VideoCamera()),mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/index', methods = ['GET'])
def index():
    return render_template('index.html')

#main
if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = '5001', debug = True)









