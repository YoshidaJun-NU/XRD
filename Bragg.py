import math

class BraggCalculator:
    def __init__(self, wavelength=1.54184):
        """
        初期化
        :param wavelength: X線の波長 (Angstrom)。
                           デフォルトは Cu K-alpha (加重平均) = 1.54184 A
                           Cu K-alpha1 = 1.54056 A などに変更可能。
        """
        self.wavelength = wavelength

    def calc_d_value(self, two_theta_deg, n=1):
        """
        2theta (度) から d値 (Angstrom) を計算します。
        式: d = n * lambda / (2 * sin(theta))
        """
        try:
            # 2thetaをthetaに変換し、さらにラジアンに変換
            theta_rad = math.radians(two_theta_deg / 2.0)
            
            sin_theta = math.sin(theta_rad)
            
            if sin_theta == 0:
                return float('inf') # 0度は無限大扱い
            
            d = (n * self.wavelength) / (2.0 * sin_theta)
            return d
            
        except ValueError as e:
            print(f"計算エラー: {e}")
            return None

    def calc_two_theta(self, d_value, n=1):
        """
        d値 (Angstrom) から 2theta (度) を計算します。
        式: theta = arcsin( n * lambda / 2d )
        """
        try:
            # sin(theta) の値を計算
            val = (n * self.wavelength) / (2.0 * d_value)
            
            # 定義域チェック (-1 <= sin(theta) <= 1)
            # 物理的には d < lambda/2 の場合、回折は起きない
            if val > 1.0:
                return None # 回折不可能
            
            theta_rad = math.asin(val)
            
            # 2theta (度) に戻す
            two_theta_deg = 2.0 * math.degrees(theta_rad)
            return two_theta_deg

        except ValueError as e:
            print(f"計算エラー: {e}")
            return None
        except ZeroDivisionError:
            print("エラー: d値に0を指定することはできません。")
            return None

# --- 実行例 ---

if __name__ == "__main__":
    # 1. 計算機のインスタンスを作成 (デフォルトは Cu K-alpha: 1.54184 A)
    # 必要なら wavelength=0.71073 (Mo) などを指定してください
    bragg = BraggCalculator(wavelength=1.54184)

    print(f"使用波長: {bragg.wavelength} Å\n")

    # ケースA: 2theta -> d値
    target_2theta = 20.0
    d_result = bragg.calc_d_value(target_2theta)
    print(f"[変換] 2θ = {target_2theta:.2f}°  ->  d = {d_result:.5f} Å")
    
    target_2theta = 40.0
    d_result = bragg.calc_d_value(target_2theta)
    print(f"[変換] 2θ = {target_2theta:.2f}°  ->  d = {d_result:.5f} Å")

    print("-" * 30)

    # ケースB: d値 -> 2theta
    target_d = 4.43
    two_theta_result = bragg.calc_two_theta(target_d)
    
    if two_theta_result:
        print(f"[変換] d = {target_d:.5f} Å  ->  2θ = {two_theta_result:.2f}°")
    else:
        print(f"[変換] d = {target_d:.5f} Å  ->  回折条件を満たしません (波長に対しdが小さすぎます)")

    # ケースC: 波長を変更する場合 (例: Mo線)
    print("-" * 30)
    mo_bragg = BraggCalculator(wavelength=0.71073)
    d_mo = mo_bragg.calc_d_value(20.0)
    print(f"Mo線 (0.71 Å) での 2θ=20° の d値: {d_mo:.5f} Å")