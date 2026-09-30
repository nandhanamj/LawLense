from django.db import models


class Act(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    source_url = models.URLField(blank=True)

    def __str__(self):
        return self.short_name


class Section(models.Model):
    act = models.ForeignKey(Act, on_delete=models.CASCADE, related_name="sections")
    section_number = models.CharField(max_length=50)
    title = models.CharField(max_length=500, blank=True)
    text = models.TextField()
    source_url = models.URLField(blank=True)

    class Meta:
        ordering = ["act", "section_number"]
        constraints = [
            models.UniqueConstraint(fields=["act", "section_number"], name="unique_act_section")
        ]

    def __str__(self):
        return f"{self.act.short_name} Section {self.section_number}"
