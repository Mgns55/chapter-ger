"""SSD1322 power-up sequence, shared by the boot splash and the display driver."""

# Init sequence for 256 x 64 SSD1322 panels (as in Newhaven's NHD-3.12 reference code).
SSD1322_INIT_SEQUENCE: tuple[tuple[int, ...], ...] = (
    (0xFD, 0x12),        # unlock commands
    (0xAE,),             # display off
    (0xB3, 0x91),        # clock divider / oscillator
    (0xCA, 0x3F),        # multiplex ratio 64
    (0xA2, 0x00),        # display offset
    (0xA1, 0x00),        # start line
    (0xA0, 0x14, 0x11),  # horizontal addressing, nibble remap, COM scan direction, dual COM
    (0xB5, 0x00),        # GPIO off
    (0xAB, 0x01),        # internal VDD regulator
    (0xB4, 0xA0, 0xFD),  # display enhancement A (external VSL)
    (0xC1, 0x9F),        # contrast current
    (0xC7, 0x0F),        # master contrast
    (0xB9,),             # default linear greyscale table
    (0xB1, 0xE2),        # phase length
    (0xD1, 0x82, 0x20),  # display enhancement B
    (0xBB, 0x1F),        # pre-charge voltage
    (0xB6, 0x08),        # second pre-charge period
    (0xBE, 0x07),        # VCOMH
    (0xA6,),             # normal display
    (0xA9,),             # exit partial display
    (0xAF,),             # display on
)
