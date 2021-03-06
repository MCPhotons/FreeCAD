# (c) 2016 Werner Mayer
# (c) 2016 Eivind Kvedalen
# LGPL

import os
import sys
import unittest
import FreeCAD
import Part
import Sketcher
import tempfile
from FreeCAD import Base

v = Base.Vector

#----------------------------------------------------------------------------------
# define the functions to test the FreeCAD Spreadsheet module and expression engine
#----------------------------------------------------------------------------------


class SpreadsheetCases(unittest.TestCase):
    def setUp(self):
        self.doc = FreeCAD.newDocument()
        self.TempPath = tempfile.gettempdir()
        FreeCAD.Console.PrintLog( '  Using temp path: ' + self.TempPath + '\n')

    def testRemoveRows(self):
        """ Removing rows -- check renaming of internal cells """
        sheet = self.doc.addObject('Spreadsheet::Sheet','Spreadsheet')
        sheet.set('A3', '123')
        sheet.set('A1', '=A3')
        sheet.removeRows('2', 1)
        self.assertEqual(sheet.getContents("A1"),"=A2")

    def testInsertRows(self):
        """ Inserting rows -- check renaming of internal cells """
        sheet = self.doc.addObject('Spreadsheet::Sheet','Spreadsheet')
        sheet.set('B1', '=B2')
        sheet.set('B2', '124')
        sheet.insertRows('2', 1)
        self.assertEqual(sheet.getContents("B1"),"=B3")

    def testRenameAlias(self):
        """ Test renaming of alias1 to alias2 in a spreadsheet """
        sheet = self.doc.addObject('Spreadsheet::Sheet','Spreadsheet')
        sheet.set('B1', '124')
        sheet.setAlias('B1', 'alias1')
        sheet.set('B2', '=alias1')
        self.doc.recompute()
        self.assertEqual(sheet.get("alias1"), 124)
        self.assertEqual(sheet.get("B1"), 124)
        self.assertEqual(sheet.get("B2"), 124)
        sheet.setAlias('B1', 'alias2')
        self.doc.recompute()
        self.assertEqual(sheet.get("alias2"), 124)
        self.assertEqual(sheet.getContents("B2"),"=alias2")

    def testRenameAlias2(self):
        """ Test renaming of alias1 to alias2 in a spreadsheet, when referenced from another object """
        sheet = self.doc.addObject('Spreadsheet::Sheet','Spreadsheet')
        sheet.set('B1', '124')
        sheet.setAlias('B1', 'alias1')
        box = self.doc.addObject('Part::Box', 'Box')
        box.setExpression('Length', 'Spreadsheet.alias1')
        sheet.setAlias('B1', 'alias2')
        self.assertEqual(box.ExpressionEngine[0][1], "Spreadsheet.alias2");

    def testRenameAlias3(self):
        """ Test renaming of document object referenced from another object """
        sheet = self.doc.addObject('Spreadsheet::Sheet','Spreadsheet')
        sheet.set('B1', '124')
        sheet.setAlias('B1', 'alias1')
        box = self.doc.addObject('Part::Box', 'Box')
        box.setExpression('Length', 'Spreadsheet.alias1')
        sheet.Label = "Params"
        self.assertEqual(box.ExpressionEngine[0][1], "Params.alias1");

    def testAlias(self):
        """ Playing with aliases """
        sheet = self.doc.addObject("Spreadsheet::Sheet","Calc")
        sheet.setAlias("A1","Test")
        self.assertEqual(sheet.getAlias("A1"),"Test")

        sheet.set("A1","4711")
        self.doc.recompute()
        self.assertEqual(sheet.get("Test"),4711)
        self.assertEqual(sheet.get("Test"),sheet.get("A1"))

    def testAmbiguousAlias(self):
        """ Try to set the same alias twice (bug #2402) """
        sheet = self.doc.addObject("Spreadsheet::Sheet","Calc")
        sheet.setAlias("A1","Test")
        try:
            sheet.setAlias("A2","Test")
            self.fail("An ambiguous alias was set which shouldn't be allowed")
        except:
            self.assertEqual(sheet.getAlias("A2"),None)

    def testClearAlias(self):
        """ This was causing a crash """
        sheet = self.doc.addObject("Spreadsheet::Sheet","Calc")
        sheet.setAlias("A1","Test")
        sheet.setAlias("A1","")
        self.assertEqual(sheet.getAlias("A1"),None)

    def testSetInvalidAlias(self):
        """ Try to use a cell address as alias name """
        sheet = self.doc.addObject("Spreadsheet::Sheet","Calc")
        try:
            sheet.setAlias("A1","B1")
        except:
            self.assertEqual(sheet.getAlias("A1"),None)
        else:
            self.fail("A cell address was used as alias which shouldn't be allowed")

    def testPlacementName(self):
        """ Object name is equal to property name (bug #2389) """
        if not FreeCAD.GuiUp:
            return
        
        import FreeCADGui
        o = self.doc.addObject("Part::FeaturePython","Placement")
        FreeCADGui.Selection.addSelection(o)

    def testInvoluteGear(self):
        """ Support of boolean or integer values """
        try:
            import InvoluteGearFeature
        except ImportError:
            return
        InvoluteGearFeature.makeInvoluteGear('InvoluteGear')
        self.doc.recompute()
        sketch=self.doc.addObject('Sketcher::SketchObject','Sketch')
        sketch.addGeometry(Part.Line(v(0,0,0),v(10,10,0)),False)
        sketch.addConstraint(Sketcher.Constraint('Distance',0,65.285388)) 
        sketch.setExpression('Constraints[0]', 'InvoluteGear.NumberOfTeeth')
        self.doc.recompute()
        self.assertIn('Up-to-date',sketch.State)

    def testSketcher(self):
        """ Mixup of Label and Name (bug #2407)"""
        sketch=self.doc.addObject('Sketcher::SketchObject','Sketch')
        sheet=self.doc.addObject('Spreadsheet::Sheet','Spreadsheet')
        sheet.setAlias('A1', 'Length')
        self.doc.recompute()
        sheet.set('A1', '47,11')
        self.doc.recompute()

        index=sketch.addGeometry(Part.Line(v(0,0,0),v(10,10,0)),False)
        sketch.addConstraint(Sketcher.Constraint('Distance',index,14.0)) 
        self.doc.recompute()
        sketch.setExpression('Constraints[0]', u'Spreadsheet.Length')
        self.doc.recompute()
        sheet.Label="Calc"
        self.doc.recompute()
        self.assertEqual(sketch.ExpressionEngine[0][1],'Calc.Length')
        self.assertIn('Up-to-date',sketch.State)

    def testCrossDocumentLinks(self):
        """ Expressions accross files are not saved (bug #2442) """

        # Create a box
        box = self.doc.addObject('Part::Box', 'Box')

        # Create a second document with a cylinder
        doc2 = FreeCAD.newDocument()
        cylinder = doc2.addObject('Part::Cylinder', 'Cylinder')
        cylinder.setExpression('Radius', 'cube#Cube.Height')

        # Save and close first document
        self.doc.saveAs(self.TempPath + os.sep + 'cube.fcstd')
        FreeCAD.closeDocument(self.doc.Name)

        # Save and close second document
        doc2.saveAs(self.TempPath + os.sep + 'cylinder.fcstd')
        FreeCAD.closeDocument(doc2.Name)

        # Open both documents again
        self.doc = FreeCAD.openDocument(self.TempPath + os.sep + 'cube.fcstd')
        doc2 = FreeCAD.openDocument(self.TempPath + os.sep + 'cylinder.fcstd')

        # Check reference between them
        self.assertEqual(doc2.getObject('Cylinder').ExpressionEngine[0][1], 'cube#Cube.Height')

        # Close second document
        FreeCAD.closeDocument(doc2.Name)

    def tearDown(self):
        #closing doc
        FreeCAD.closeDocument(self.doc.Name)
