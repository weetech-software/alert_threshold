class Config:
    def __init__(self, description: str, enable: bool, script: str, metrics: list[str], exclude_hosts: list[str], value: float, operator: str, threshold_operator: str, alert_value: int, alert_methods: list[str]) -> None:
        self.description = description
        self.enable = enable
        self.script = script
        self.metrics = metrics
        self.exclude_hosts = exclude_hosts
        self.value = value
        self.operator = operator
        self.threshold_operator = threshold_operator
        self.alert_value = alert_value
        self.alert_methods = alert_methods

    def __str__(self) -> str:
        return (
            f"description: {self.description}, enable: {self.enable}, script: {self.script}, "
            f"metrics: [{','.join(self.metrics)}], exclude_hosts: [{','.join(self.exclude_hosts)}], "
            f"value: {self.value}, operator: {self.operator}, threshold_operator: {self.threshold_operator}, "
            f"alert_value: {self.alert_value}, alert_methods: [{','.join(self.alert_methods)}]"
        )

    def __repr__(self) -> str:
        return self.__str__()

