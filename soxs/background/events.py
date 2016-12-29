import numpy as np
import os
import astropy.io.fits as pyfits
from soxs.utils import mylog

key_map = {"telescope": "TELESCOP",
           "mission": "MISSION",
           "instrument": "INSTRUME",
           "channel_type": "CHANTYPE",
           "nchan": "PHA_BINS"}

def add_background_from_file(events, event_params, bkg_file):
    f = pyfits.open(bkg_file)

    hdu = f["EVENTS"]

    sexp = event_params["exposure_time"]
    bexp = hdu.header["EXPOSURE"]

    if event_params["exposure_time"] > hdu.header["EXPOSURE"]:
        raise RuntimeError("The bagkround file does not have sufficient exposure! Source "
                           "exposure time %g, background exposure time %g." % (sexp, bexp))

    for k1, k2 in key_map.items():
        if event_params[k1] != hdu.header[k2]:
            raise RuntimeError("'%s' keyword does not match! %s vs. %s" % (k1, event_params[k1],
                                                                           hdu.header[k2]))
    rmf1 = os.path.split(event_params["rmf"])[-1]
    rmf2 = hdu.header["RESPFILE"]
    arf1 = os.path.split(event_params["arf"])[-1]
    arf2 = hdu.header["ANCRFILE"]
    if rmf1 != rmf2:
        raise RuntimeError("RMFs do not match! %s vs. %s" % (rmf1, rmf2))
    if arf1 != arf2:
        raise RuntimeError("ARFs do not match! %s vs. %s" % (arf1, arf2))

    idxs = hdu.data["TIME"] < sexp

    mylog.info("Adding %d background events from %s." % (idxs.sum(), bkg_file))

    if event_params["roll_angle"] == hdu.header["ROLL_PNT"]:
        xpix = hdu.data["X"][idxs]
        ypix = hdu.data["Y"][idxs]
    else:
        roll_angle = np.deg2rad(event_params["roll_angle"])
        rot_mat = np.array([[np.sin(roll_angle), -np.cos(roll_angle)],
                            [-np.cos(roll_angle), -np.sin(roll_angle)]])
        xpix, ypix = np.dot(rot_mat, np.array([hdu.data["DETX"][idxs], hdu.data["DETY"][idxs]]))
        xpix += hdu.header["TCRPX2"]
        ypix += hdu.header["TCRPX3"]

    all_events = {}
    for key in ["chipx", "chipy", "detx", "dety", "energy", "time", event_params["channel_type"]]:
        all_events[key] = np.concatenate([events[key], hdu.data[key.upper()][idxs]])
    all_events["xpix"] = np.concatenate([events["xpix"], xpix])
    all_events["ypix"] = np.concatenate([events["ypix"], ypix])

    f.close()

    return all_events