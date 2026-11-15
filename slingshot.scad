// Card-style slingshot, parametric. Original design (not a copy of any MakerWorld file).
// Edit the values below, then F6 + Export STL in OpenSCAD, or:
//   openscad -o slingshot.stl slingshot.scad
//   openscad -o slingshot.stl -D 'thickness=8' -D 'band_style="slot"' slingshot.scad

/* [Card] */
card_w     = 54;    // width  (credit card short side)
card_h     = 85.6;  // height (credit card long side)
thickness  = 6;     // PLA: >=6 for light bands, PETG/PA-CF recommended
corner_r   = 4;

/* [Fork] */
gap_w      = 28;    // opening between the prongs
gap_depth  = 40;    // how deep the opening goes into the card

/* [Band attachment] */
band_style = "groove"; // "groove" = wrap & tie, "slot" = thread flat band through, "none"
groove_y   = 6;     // groove centre, measured down from the prong tip
groove_w   = 4;     // groove height (fits ~3 wraps of thread / tube)
groove_d   = 1.2;   // groove depth into the prong
slot_w     = 2;     // slot thickness (flat band thickness + clearance)
slot_len   = 9;     // slot length across the prong

/* [Grip] */
finger_d   = 20;    // finger hole, 0 = none
lanyard_d  = 4;     // lanyard hole in bottom corner, 0 = none

/* [Text] */
label      = "";    // engraved on the front face, "" = none
label_size = 5;
label_depth= 0.6;

$fn = 64;

prong_w = (card_w - gap_w) / 2;
handle_h = card_h - gap_depth;

module outline() {
    difference() {
        offset(r = corner_r) offset(delta = -corner_r) square([card_w, card_h]);
        // fork opening with rounded bottom (avoids a stress corner)
        translate([prong_w, card_h - gap_depth + gap_w/2]) square([gap_w, card_h]);
        translate([card_w/2, card_h - gap_depth + gap_w/2]) circle(d = gap_w);
        if (finger_d > 0) translate([card_w/2, handle_h/2]) circle(d = finger_d);
        if (lanyard_d > 0) translate([corner_r + lanyard_d, corner_r + lanyard_d]) circle(d = lanyard_d);
    }
}

module band_cut(x0) {   // x0 = left edge of the prong
    y = card_h - groove_y;
    if (band_style == "groove")
        // ring around the prong: big box minus the prong core
        difference() {
            translate([x0 - 1, y - groove_w/2, -1]) cube([prong_w + 2, groove_w, thickness + 2]);
            translate([x0 + groove_d, y - groove_w/2 - 1, groove_d])
                cube([prong_w - 2*groove_d, groove_w + 2, thickness - 2*groove_d]);
        }
    else if (band_style == "slot")
        translate([x0 + (prong_w - slot_len)/2, y - slot_w/2, -1]) cube([slot_len, slot_w, thickness + 2]);
}

difference() {
    linear_extrude(thickness) outline();
    band_cut(0);
    band_cut(card_w - prong_w);
    if (label != "")
        translate([card_w/2, handle_h/2 - finger_d/2 - label_size - 2, thickness - label_depth])
            linear_extrude(label_depth + 1)
                text(label, size = label_size, halign = "center", font = "Liberation Sans:style=Bold");
}

assert(prong_w >= 8, "prongs thinner than 8 mm will snap - reduce gap_w");
assert(groove_d * 2 < min(prong_w, thickness) - 3, "groove too deep for prong");
