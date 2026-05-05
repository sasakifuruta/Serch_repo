# --- 1. 基本となるクラス定義 ---
class Creature:
    """クリーチャーの基本クラス（カプセル化）"""
    def __init__(self, name, health, attack_power):
        self.__name = name  # __でカプセル化（外部から隠す）
        self.health = health
        self.attack_power = attack_power

    def attack(self, other):
        print(f"{self.__name}の攻撃！")
        other.take_damage(self.attack_power)

    def take_damage(self, damage):
        self.health -= damage
        print(f"{self.__name}は {damage} のダメージを受けた。残HP: {self.health}")

    def is_alive(self):
        return self.health > 0

    def get_name(self):
        return self.__name

# --- 2. 継承の例 ---
class Warrior(Creature):
    """基本クラスを継承した勇者クラス"""
    def special_move(self, other):
        print(f"{self.get_name()}の強力な一撃！")
        other.take_damage(self.attack_power * 2)

# --- 3. ポリモーフィズムの例 ---
class Monster(Creature):
    """基本クラスを継承したモンスタークラス"""
    def take_damage(self, damage):
        # モンスターは防御力が高いという特性（メソッドのオーバーライド）
        actual_damage = max(0, damage - 2)
        super().take_damage(actual_damage)

# --- 4. 実行部分 ---
if __name__ == "__main__":
    hero = Warrior("勇者", health=100, attack_power=20)
    monster = Monster("スライム", health=50, attack_power=10)

    # バトル開始
    print(f"=== {hero.get_name()} vs {monster.get_name()} ===")
    
    # ターン1
    hero.attack(monster)
    
    # ターン2
    if monster.is_alive():
        monster.attack(hero)
        
    # ターン3（スペシャル）
    hero.special_move(monster)

    print(f"最終結果: {'勇者の勝利' if not monster.is_alive() else 'モンスターの勝利'}")
