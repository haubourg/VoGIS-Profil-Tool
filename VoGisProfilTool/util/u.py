# -*- coding: iso-8859-15 -*-

from os.path import basename
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import ogr
import osr
from qgis.core import QgsVectorFileWriter
from qgis.core import QgsPoint
from qgis.core import QgsGeometry
from qgis.core import QgsFeature
from qgis.core import QgsMessageLog
from qgis.core import QGis
from ..bo.node import Node
from ..bo.linkedList import LinkedList


class Util:

    @staticmethod
    def t(txt):
        return QApplication.translate('code', txt, None, QApplication.UnicodeUTF8)

    def __init__(self, iface):
        self.iface = iface

    def isFloat(self, val, valName):
        try:
            val = val.replace(',', '.')
            f = float(val)
            f += 0.01
            return True
        except:
            #QMessageBox.warning(self.iface.mainWindow(), "VoGIS-Profiltool", unicode(valName) + u' ' + unicode(QApplication.translate('code', u'ist keine gültige Zahl!', None, QApplication.UnicodeUTF8)))
            QMessageBox.warning(self.iface.mainWindow(), "VoGIS-Profiltool", '"' + valName + '" ' + QApplication.translate('code', 'ist keine gültige Zahl!', None, QApplication.UnicodeUTF8))
            #QMessageBox.warning(self.iface.mainWindow(), "VoGIS-Profiltool", tr(u'ist keine gültige Zahl!'))
            return False

    def isInt(self, val, valName):
        try:
            i = int(val)
            i += 1
            return True
        except:
            QMessageBox.warning(self.iface.mainWindow(), "VoGIS-Profiltool", u"'" + valName + "' ist keine gültige Ganzzahl!")
            return False

    def getFileName(self, text, filter, filePath):
        selectedFilter = QString()
        fileDlg = QFileDialog(self.iface.mainWindow())
        fileName = fileDlg.getSaveFileName(self.iface.mainWindow(),
                                           text,
                                           filePath,
                                           filter,
                                           selectedFilter,
                                           )
        if fileName.isEmpty():
            return ''
        fileExt = str(selectedFilter[:3]).lower()
        #fileExt = fInfo.suffix()
        fileName = unicode(fileName)
        if fileName.lower().endswith(fileExt) is False:
            fileName = fileName + '.' + fileExt
        return fileName

    def createQgLineFeature(self, vertices):
        line = QgsGeometry.fromPolyline(vertices)
        qgFeat = QgsFeature()
        qgFeat.setGeometry(line)
        return qgFeat

    def createQgPointFeature(self, vertex):
        pnt = QgsGeometry.fromPoint(QgsPoint(vertex.x, vertex.y))
        qgPnt = QgsFeature()
        qgPnt.setGeometry(pnt)
        return qgPnt

    def prepareFeatures(self, settings, provider, origFeats):
        """explode multipart features"""
        """merge lines with same direction and same start and end vertices"""

        newFeats = None

        if settings.linesExplode is True:
            newFeats = self.__explodeMultiPartFeatures(provider, origFeats)
            #self.__printAttribs(newFeats[0].attributeMap())

        if settings.linesMerge is True:
            newFeats = self.__mergeFeaturesAny(newFeats)
            #self.__printAttribs(newFeats[0].attributeMap())

            newFeats = self.__mergeFeaturesSimple(provider, newFeats)
            #self.__printAttribs(newFeats[0].attributeMap())

        if newFeats is None:
            return origFeats
        else:
            return newFeats

    def __mergeFeaturesAny(self, origFeats):
        ll = LinkedList()
        for idx, feat in enumerate(origFeats):
            n = Node(idx)
            featPnts = feat.geometry().asPolyline()
            for i, f in enumerate(origFeats):
                if idx == i:
                    continue
                fPnts = f.geometry().asPolyline()
                if featPnts[len(featPnts) - 1] == fPnts[0]:
                    n.setNext(i)
                if featPnts[0] == fPnts[len(fPnts) - 1]:
                    n.setPrev(i)
            ll.addNode(n)

        #for n in ll.nodes:
        #    QgsMessageLog.logMessage('{0}'.format(n.toString()), 'VoGis')

        newFeats = []
        orderedIds = ll.getOrderedIds()
        #QgsMessageLog.logMessage('{0}'.format(orderedIds), 'VoGis')
        for idx in orderedIds:
            newFeats.append(origFeats[idx])

        return newFeats

    def __mergeFeaturesSimple(self, provider, origFeats):

        newFeats = []
        QgsMessageLog.logMessage('---- Merge Simple: {0} features'.format(len(origFeats)), 'VoGis')

        prevToPnt = None
        #newGeom = QgsGeometry()
        newGeom = QgsGeometry().fromPolyline([])
        attrMap = None
        #newGeom = QgsGeometry.fromPolyline([QgsPoint(1, 1), QgsPoint(2, 2)])
        #QgsMessageLog.logMessage('newGeom WKB Type {0}'.format(newGeom.wkbType() == QGis.WKBLineString), 'VoGis')
        for feat in origFeats:
            #QgsMessageLog.logMessage('{0}:{1}'.format('ORIG FEAT AttributeMap', self.__printAttribs(feat.attributeMap())), 'VoGis')
            #self.__printAttribs(feat.attributeMap())
            currentGeom = feat.geometry()
            currentPnts = currentGeom.asPolyline()
            if prevToPnt is None:
                #QgsMessageLog.logMessage('combining FIRST {0}'.format(currentGeom.asPolyline()), 'VoGis')
                newGeom = newGeom.combine(currentGeom)
                attrMap = feat.attributeMap()
            else:
                if currentPnts[0] == prevToPnt:
                    #QgsMessageLog.logMessage('combining {0}'.format(currentGeom.asPolyline()), 'VoGis')
                    newGeom = newGeom.combine(currentGeom)
                    attrMap = feat.attributeMap()
                else:
                    #QgsMessageLog.logMessage('creating {0}'.format(newGeom.asPolyline()), 'VoGis')
                    featNew = self.createQgLineFeature(newGeom.asPolyline())
                    featNew = self.__transferAttributes(provider, attrMap, featNew)
                    newFeats.append(featNew)
                    #feat = QgsFeature()
                    #newGeom = QgsGeometry()
                    newGeom = QgsGeometry().fromPolyline(currentPnts)
                    attrMap = feat.attributeMap()
                #newGeom = QgsGeometry.fromPolyline([QgsPoint(1, 1), QgsPoint(2, 2)])

            prevToPnt = currentPnts[len(currentPnts) - 1]

        featNew = self.createQgLineFeature(newGeom.asPolyline())
        self.__transferAttributes(provider, attrMap, featNew)
        #newFeats.append(self.createQgLineFeature(newGeom.asPolyline()))
        newFeats.append(featNew)

        QgsMessageLog.logMessage('---- {0} features after Merge Simple'.format(len(newFeats)), 'VoGis')

        #for idx, f in enumerate(newFeats):
        #    QgsMessageLog.logMessage('--------feature {0}---------'.format(idx), 'VoGis')
        #    geo = f.geometry()
        #    pnts = geo.asPolyline()
        #    for i, v in enumerate(pnts):
        #        QgsMessageLog.logMessage('   pnt {0}: {1}/{2}'.format(i, v.x(), v.y()), 'VoGis')

        return newFeats

    def __printAttribs(self, attributeMap):
        txt = ''
        for (k, attr) in attributeMap.iteritems():
            txt += '({0}: {1}) '.format(k, attr.toString())
        return txt

    def __explodeMultiPartFeatures(self, provider, origFeats):

        newFeats = []
        QgsMessageLog.logMessage('exploding {0} features'.format(len(origFeats)), 'VoGis')

        for feat in origFeats:
            geom = feat.geometry()
            if geom.isMultipart():
                #QgsMessageLog.logMessage('FId[{0}]: {1}'.format(feat.id(), 'multipart feature!'), 'VoGis')
                newFeats.extend(self.explodeMultiPartFeature(provider, feat))
            else:
                #QgsMessageLog.logMessage('FId[{0}]: {1}'.format(feat.id(), 'single part feature'), 'VoGis')
                newFeats.append(feat)

        QgsMessageLog.logMessage('{0} features after exploding'.format(len(newFeats)), 'VoGis')
        return newFeats

    #https://github.com/SrNetoChan/MultipartSplit/blob/master/splitmultipart.py
    def explodeMultiPartFeature(self, provider, feat):

        tmpFeat = QgsFeature()

        # Get attributes from original feature
        # Because of changes in the way the 1.9 api handle attributes
        if QGis.QGIS_VERSION_INT < 10900:
            newAttribs = feat.attributeMap()
            for j in range(newAttribs.__len__()):
                if not provider.defaultValue(j).isNull():
                    newAttribs[j] = provider.defaultValue(j)
            tmpFeat.setAttributeMap(newAttribs)
        else:
            newAttribs = feat.attributes()
            for j in range(newAttribs.__len__()):
                if not provider.defaultValue(j).isNull():
                    newAttribs[j] = provider.defaultValue(j)
            tmpFeat.setAttributes(newAttribs)

        parts = feat.geometry().asGeometryCollection()

        newFeats = []
        for i in range(len(parts)):
            tmpFeat.setGeometry(parts[i])
            newFeats.append(QgsFeature(tmpFeat))

        return newFeats

    def __transferAttributes(self, provider, attrMap, featNew):
        #QgsMessageLog.logMessage('{0}: {1}'.format('__transferAttributes OLD', self.__printAttribs(attrMap)), 'VoGis')
        #QgsMessageLog.logMessage('{0}: {1}'.format('__transferAttributes NEW', self.__printAttribs(featNew.attributeMap())), 'VoGis')

        if QGis.QGIS_VERSION_INT < 10900:
            newAttribs = attrMap
            for j in range(newAttribs.__len__()):
                if not provider.defaultValue(j).isNull():
                    newAttribs[j] = provider.defaultValue(j)
            featNew.setAttributeMap(newAttribs)
        else:
            newAttribs = attrMap
            for j in range(newAttribs.__len__()):
                if not provider.defaultValue(j).isNull():
                    newAttribs[j] = provider.defaultValue(j)
            featNew.setAttributes(newAttribs)

        #QgsMessageLog.logMessage('{0}: {1}'.format('__transferAttributes NEW2', self.__printAttribs(featNew.attributeMap())), 'VoGis')
        return featNew

    def deleteVectorFile(self, fileName):
        if QgsVectorFileWriter.deleteShapeFile(fileName) is False:
            QMessageBox.warning(self.iface.mainWindow(),
                                "VoGIS-Profiltool",
                                QApplication.translate('code', 'Konnte vorhandene Datei nicht löschen', None, QApplication.UnicodeUTF8) + ': ' + fileName
                                )
            return False
        else:
            return True

    def loadVectorFile(self, fileName):
        fileSaved = QApplication.translate('code', 'Datei gespeichert.', None, QApplication.UnicodeUTF8)
        load =QApplication.translate('code', 'Laden?', None, QApplication.UnicodeUTF8)
        reply = QMessageBox.question(self.iface.mainWindow(),
                                     "VoGIS-Profiltool",
                                     fileSaved + '\r\n\r\n\r\n' + load,
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.Yes
                                     )
        if reply == QMessageBox.Yes:
            self.iface.addVectorLayer(fileName,
                                      basename(str(fileName)),
                                      'ogr'
                                      )

    def createOgrDataSrcAndLyr(self, driverName, fileName, epsg, geomType):

        drv = ogr.GetDriverByName(driverName)
        if drv is None:
            QMessageBox.warning(self.iface.mainWindow(),
                                "VoGIS-Profiltool",
                                driverName + ' ' + QApplication.translate('code', 'Treiber nicht verfügbar', None, QApplication.UnicodeUTF8)
                                )
            return None, None

        ds = drv.CreateDataSource(fileName)
        if ds is None:
            QMessageBox.warning(self.iface.mainWindow(),
                                "VoGIS-Profiltool",
                                QApplication.translate('code', 'Konnte Datei nicht erstellen', None, QApplication.UnicodeUTF8) + ': ' + driverName + ', ' + fileName
                                )
            return None, None

        if epsg is None:
            spatialReference = None
        else:
            spatialReference = osr.SpatialReference()
            if spatialReference.ImportFromEPSG(epsg) != 0:
                QMessageBox.warning(self.iface.mainWindow(),
                                    "VoGIS-Profiltool",
                                    QApplication.translate('code', 'Konnte Koordinatensystem nicht initialisieren!', None, QApplication.UnicodeUTF8) + ' EPSG: {0}'.format(epsg)
                                    )
                return None, None
        #http://www.digital-geography.com/create-and-edit-shapefiles-with-python-only/
        lyr = ds.CreateLayer("ogrlyr", spatialReference, geomType)
        if lyr is None:
            QMessageBox.warning(self.iface.mainWindow(),
                                "VoGIS-Profiltool",
                                QApplication.translate('code', 'Konnte Layer nicht erstellen', None, QApplication.UnicodeUTF8) + ': {0}, {1}'.format(driverName, fileName)
                                )
            return None, None

        return ds, lyr

    def createOgrPointFeature(self, lyr, v):
        #QgsMessageLog.logMessage('zVal: {0}'.format(v.zvals[0]), 'VoGis')
        feat = ogr.Feature(lyr.GetLayerDefn())
        pt = ogr.Geometry(ogr.wkbPoint25D)
        z = 0
        if len(v.zvals) > 0:
            z = v.zvals[0]
        pt.SetPoint(0, v.x, v.y, z)
        feat.SetGeometry(pt)
        return feat