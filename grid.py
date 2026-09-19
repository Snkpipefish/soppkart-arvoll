import math, json
Z=15
LAT0,LAT1,LON0,LON1=59.940,59.986,10.780,10.870
def ll2tile(lat,lon,z):
    n=2**z
    x=(lon+180)/360*n
    y=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n
    return x,y
x0,y1=ll2tile(LAT0,LON0,Z); x1,y0=ll2tile(LAT1,LON1,Z)
TX0,TX1=int(math.floor(x0)),int(math.floor(x1))
TY0,TY1=int(math.floor(y0)),int(math.floor(y1))
NX,NY=TX1-TX0+1,TY1-TY0+1
R=6378137.0
def tile2merc(tx,ty,z):
    n=2**z
    mx=(tx/n*2-1)*math.pi*R
    my=(1-ty/n*2)*math.pi*R
    return mx,my
MX0,MY1=tile2merc(TX0,TY0,Z)      # top-left
MX1,MY0=tile2merc(TX1+1,TY1+1,Z)  # bottom-right
def merc2ll(mx,my):
    lon=math.degrees(mx/R); lat=math.degrees(2*math.atan(math.exp(my/R))-math.pi/2); return lat,lon
if __name__=="__main__":
    print("tiles x",TX0,TX1,"y",TY0,TY1,"n",NX,NY,"px",NX*256,NY*256)
    print("merc",MX0,MY0,MX1,MY1)
    print("SW",merc2ll(MX0,MY0),"NE",merc2ll(MX1,MY1))
    json.dump(dict(Z=Z,TX0=TX0,TX1=TX1,TY0=TY0,TY1=TY1,MX0=MX0,MY0=MY0,MX1=MX1,MY1=MY1,SW=merc2ll(MX0,MY0),NE=merc2ll(MX1,MY1)),open('data/grid.json','w'))
