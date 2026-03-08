import unittest
from pylutron import Lutron, LutronXmlDbParser

# Anonymized XML based on the real DbXmlInfo.xml structure
LEGACY_AND_COMPLEX_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<Project>
    <ProjectName ProjectName="Anonymized House" UUID="1" />
    <GUID>7ccee645777f46459a3d5216b6e54d5a</GUID>
    <Areas>
        <Area Name="House" UUID="3" IntegrationID="0" OccupancyGroupAssignedToID="0" SortOrder="0">
            <Areas>
                <Area Name="Master Bedroom" UUID="407" IntegrationID="16" OccupancyGroupAssignedToID="409">
                    <DeviceGroups>
                        <DeviceGroup Name="Main">
                            <Devices>
                                <Device Name="Master Keypad" UUID="7501" IntegrationID="34" DeviceType="PALLADIOM_KEYPAD">
                                    <Components>
                                        <Component ComponentNumber="1" ComponentType="BUTTON">
                                            <Button Engraving="On" ButtonType="Toggle" UUID="B1" />
                                        </Component>
                                    </Components>
                                </Device>
                            </Devices>
                        </DeviceGroup>
                    </DeviceGroups>
                </Area>
                <Area Name="Kitchen" UUID="357" IntegrationID="11" OccupancyGroupAssignedToID="359">
                    <DeviceGroups>
                        <DeviceGroup Name="Stairs">
                            <Devices>
                                <Device Name="Pico" UUID="9555" IntegrationID="28" DeviceType="PICO_KEYPAD">
                                    <Components>
                                        <Component ComponentNumber="5" ComponentType="BUTTON">
                                            <Button Engraving="Raise" ButtonType="SingleSceneRaiseLower" Direction="Raise" UUID="B2" />
                                        </Component>
                                    </Components>
                                </Device>
                            </Devices>
                        </DeviceGroup>
                    </DeviceGroups>
                </Area>
            </Areas>
        </Area>
    </Areas>
    <OccupancyGroups>
        <OccupancyGroup UUID="409" OccupancyGroupNumber="409" />
        <OccupancyGroup UUID="359" OccupancyGroupNumber="359" />
    </OccupancyGroups>
</Project>
"""

# Minimal XML for testing
MINIMAL_XML = """
<Lutron>
    <GUID>12345678-ABCD-1234-ABCD-1234567890AB</GUID>
    <OccupancyGroups>
        <OccupancyGroup UUID="OCC-1" OccupancyGroupNumber="1" />
    </OccupancyGroups>
    <Areas>
        <Area Name="Project">
            <Areas>
                <Area Name="Living Room" IntegrationID="1" OccupancyGroupAssignedToID="1">
                    <Outputs>
                        <Output Name="Sconce" IntegrationID="2" OutputType="NON_DIM" Wattage="100" UUID="OUT-1" />
                    </Outputs>
                    <DeviceGroups>
                        <DeviceGroup Name="Wall Keypad">
                             <Devices>
                                 <Device Name="Main" IntegrationID="3" DeviceType="SEETOUCH_KEYPAD" UUID="DEV-1">
                                    <Components>
                                        <Component ComponentNumber="1" ComponentType="BUTTON">
                                            <Button Engraving="On" ButtonType="Toggle" Direction="Press" UUID="BTN-1" />
                                        </Component>
                                    </Components>
                                 </Device>
                             </Devices>
                        </DeviceGroup>
                    </DeviceGroups>
                </Area>
            </Areas>
        </Area>
    </Areas>
</Lutron>
"""

class TestLutronXmlDbParser(unittest.TestCase):
    def setUp(self) -> None:
        self.lutron = Lutron('localhost', 'user', 'pass')

    def test_parse_simple_xml(self) -> None:
        parser = LutronXmlDbParser(self.lutron, MINIMAL_XML)
        self.assertTrue(parser.parse())
        
        # Check Project Info
        # GUID is set on the lutron object
        self.assertEqual(self.lutron.guid, '12345678-ABCD-1234-ABCD-1234567890AB')
        # Name and areas are stored in the parser until loaded
        self.assertEqual(parser.project_name, 'Project')
        
        # Check Areas
        self.assertEqual(len(parser.areas), 1)
        area = parser.areas[0]
        self.assertEqual(area.name, 'Living Room')
        self.assertEqual(area.id, 1)

    def test_parse_outputs(self) -> None:
        parser = LutronXmlDbParser(self.lutron, MINIMAL_XML)
        parser.parse()
        area = parser.areas[0]
        
        self.assertEqual(len(area.outputs), 1)
        output = area.outputs[0]
        self.assertEqual(output.name, 'Sconce')
        self.assertEqual(output.watts, 100)
        self.assertEqual(output.type, 'NON_DIM')
        self.assertEqual(output.id, 2)

    def test_parse_keypad(self) -> None:
        parser = LutronXmlDbParser(self.lutron, MINIMAL_XML)
        parser.parse()
        area = parser.areas[0]
        
        self.assertEqual(len(area.keypads), 1)
        keypad = area.keypads[0]
        self.assertEqual(keypad.name, 'Main')
        self.assertEqual(keypad.location, 'Wall Keypad')
        
        # Check Buttons
        self.assertEqual(len(keypad.buttons), 1)
        button = keypad.buttons[0]
        self.assertEqual(button.name, 'On')
        self.assertEqual(button.number, 1)

    def test_palladiom_keypad_parsing(self) -> None:
        parser = LutronXmlDbParser(self.lutron, LEGACY_AND_COMPLEX_XML)
        parser.parse()
        
        mbr = next(a for a in parser.areas if a.name == "Master Bedroom")
        keypad = mbr.keypads[0]
        self.assertEqual(keypad.type, "PALLADIOM_KEYPAD")
        self.assertEqual(len(keypad.buttons), 1)

    def test_pico_raise_lower_naming(self) -> None:
        parser = LutronXmlDbParser(self.lutron, LEGACY_AND_COMPLEX_XML)
        parser.parse()
        
        kitchen = next(a for a in parser.areas if a.name == "Kitchen")
        pico = kitchen.keypads[0]
        btn = pico.buttons[0]
        self.assertEqual(btn.name, "Dimmer Raise")

if __name__ == '__main__':
    unittest.main()
