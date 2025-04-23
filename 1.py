def bb(var1):
    if len(var1) == 0:
        return "0,0,0"
    else:
        var1.sort()
        print(var1.sort())
        c = var1[0]
        d = var1[-1]
        var2 = 90 / 100.0
        var3 = 95 / 100.0
        var4 = 99 / 100.0
        var5 = {}

        if not var5:
            var5[var2] = 0
            var5[var3] = 0
            var5[var4] = 0

        for key in var5.keys():
            var8 = round(len(var1) * key)
            # var8 =25

            for var10 in range(len(var1)):
                if var8 == 0:
                    var5[key] = var1[var10]
                    break
                var8 -= 1

        return f"{var5[var2]},{var5[var3]},{var5[var4]}"

print(bb([1,2,3,545,4225,4242,34]))